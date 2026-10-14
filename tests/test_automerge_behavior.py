"""Integration-level, no-network simulation of the privileged Dependabot gate.

The exact Python embedded in the workflow is exercised against an in-process
fake GitHub API. No real merge, token, repository, or external network is used.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/dependabot-automerge.yml'
HEAD = 'a' * 40


def gate_code():
    content = WORKFLOW.read_text(encoding='utf-8')
    match = re.search(r"          python - <<'PY'\n(.*?)\n          PY", content, re.S)
    if not match:
        raise AssertionError('Embedded Dependabot script was removed or changed')
    script = '\n'.join(line[10:] for line in match.group(1).splitlines())
    compile(script, str(WORKFLOW), 'exec')
    return script


class FakeGitHubAPI:
    def __init__(self, *, pending_extra=False, failed_extra=False, altered_sha=False,
                 behind=0, bad_vercel=False, base='main'):
        self.pending_extra = pending_extra
        self.failed_extra = failed_extra
        self.altered_sha = altered_sha
        self.behind = behind
        self.bad_vercel = bad_vercel
        self.base = base
        self.merges = []
        self.server = None

    def __enter__(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, data, code=200):
                out = json.dumps(data).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            def do_GET(self):
                path = self.path.split('?')[0]
                if path == '/repos/Nisan-Sinai/example/pulls/5':
                    return self.reply({'state': 'open', 'draft': False,
                                       'user': {'login': 'dependabot[bot]'},
                                       'head': {'sha': 'b' * 40 if api.altered_sha else HEAD},
                                       'base': {'ref': api.base},
                                       'mergeable': True, 'mergeable_state': 'clean'})
                if path == '/repos/Nisan-Sinai/example/':
                    return self.reply({'default_branch': 'main'})
                if path == f'/repos/Nisan-Sinai/example/compare/main...{HEAD}':
                    return self.reply({'behind_by': api.behind})
                if path == f'/repos/Nisan-Sinai/example/commits/{HEAD}/check-runs':
                    rows = [{'id': 11, 'name': 'CI', 'status': 'completed', 'conclusion': 'success'}]
                    if api.pending_extra:
                        rows.append({'id': 12, 'name': 'Other security check', 'status': 'in_progress', 'conclusion': None})
                    if api.failed_extra:
                        rows.append({'id': 13, 'name': 'Secret scan', 'status': 'completed', 'conclusion': 'failure'})
                    return self.reply({'check_runs': rows})
                if path == f'/repos/Nisan-Sinai/example/commits/{HEAD}/statuses':
                    return self.reply([{'context': 'Vercel', 'state': 'success',
                                        'creator': {'login': 'attacker' if api.bad_vercel else 'vercel[bot]'},
                                        'target_url': 'https://vercel.com/team/project/deployment'}])
                return self.reply({'message': path}, 404)

            def do_PUT(self):
                if self.path == '/repos/Nisan-Sinai/example/pulls/5/merge':
                    data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
                    api.merges.append(data)
                    return self.reply({'merged': True})
                return self.reply({'message': 'unknown'}, 404)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.worker = Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def invoke(self, **overrides):
        env = dict(os.environ, REPOSITORY='Nisan-Sinai/example', PR_NUMBER='5',
                   PR_SHA=HEAD, UPDATE_TYPE='version-update:semver-patch',
                   REQUIRED_CHECKS='["CI"]', REQUIRED_STATUSES='["Vercel"]',
                   ENABLE_MERGE='true', GH_TOKEN='fake-test-token',
                   GITHUB_API_URL=f'http://127.0.0.1:{self.server.server_port}')
        env.update(overrides)
        return subprocess.run([sys.executable, '-c', gate_code()],
                              env=env, text=True, capture_output=True, timeout=7)


class DependabotGateTests(unittest.TestCase):
    def test_clean_patch_merge_exact_sha(self):
        with FakeGitHubAPI() as api:
            completed = api.invoke()
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(api.merges, [{'sha': HEAD, 'merge_method': 'squash'}])

    def test_dry_run_never_writes(self):
        with FakeGitHubAPI() as api:
            completed = api.invoke(ENABLE_MERGE='false')
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(api.merges, [])

    def test_major_never_writes(self):
        with FakeGitHubAPI() as api:
            completed = api.invoke(UPDATE_TYPE='version-update:semver-major')
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(api.merges, [])

    def test_empty_or_malformed_required_checks_fail_closed(self):
        with FakeGitHubAPI() as api:
            for raw in ('[]', '["CI", "CI"]', '{}', 'not-json'):
                with self.subTest(value=raw):
                    self.assertNotEqual(api.invoke(REQUIRED_CHECKS=raw).returncode, 0)
            self.assertEqual(api.merges, [])

    def test_extra_failed_check_blocks_merge(self):
        with FakeGitHubAPI(failed_extra=True) as api:
            self.assertNotEqual(api.invoke().returncode, 0)
            self.assertEqual(api.merges, [])

    def test_extra_pending_check_blocks_merge_without_timeout(self):
        # The first poll must NOT merge while an unlisted quality/security check is running.
        # The workflow is bounded by a 35-minute CI timeout; the test sends one request,
        # and expects no dangerous merge before the process is stopped.
        with FakeGitHubAPI(pending_extra=True) as api:
            import time
            proc = subprocess.Popen([sys.executable, '-c', gate_code()],
                    env={**os.environ, 'REPOSITORY': 'Nisan-Sinai/example',
                         'PR_NUMBER': '5', 'PR_SHA': HEAD,
                         'UPDATE_TYPE': 'version-update:semver-patch',
                         'REQUIRED_CHECKS': '["CI"]', 'REQUIRED_STATUSES': '["Vercel"]',
                         'ENABLE_MERGE': 'true', 'GH_TOKEN': 'fake-test-token',
                         'GITHUB_API_URL': f'http://127.0.0.1:{api.server.server_port}'},
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                time.sleep(0.5)
                self.assertEqual(api.merges, [], 'Pending unknown check was bypassed!')
            finally:
                proc.terminate()
                proc.communicate(timeout=3)

    def test_changed_sha_blocks_merge(self):
        with FakeGitHubAPI(altered_sha=True) as api:
            self.assertNotEqual(api.invoke().returncode, 0)
            self.assertEqual(api.merges, [])

    def test_behind_base_blocks_merge(self):
        with FakeGitHubAPI(behind=1) as api:
            self.assertNotEqual(api.invoke().returncode, 0)
            self.assertEqual(api.merges, [])

    def test_fake_vercel_sender_blocks_merge(self):
        with FakeGitHubAPI(bad_vercel=True) as api:
            self.assertNotEqual(api.invoke().returncode, 0)
            self.assertEqual(api.merges, [])


if __name__ == '__main__':
    unittest.main()
