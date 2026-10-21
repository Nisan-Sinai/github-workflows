"""Execute the real shared report gate, including forged PASS and failure cases."""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import parse_yaml


class IsolatedLoadTests(unittest.TestCase):
    def evaluate(self, report):
        flow = parse_yaml(ROOT / '.github/workflows/isolated-load-qa.yml')
        step = next(s for s in flow['jobs']['load']['steps']
                    if s.get('name') == 'Benchmark local public GET routes only')
        javascript = step['run'].split("node --input-type=module - <<'NODE'", 1)[1]
        javascript = javascript.split('\n', 1)[1].split('\nNODE', 1)[0]
        with tempfile.TemporaryDirectory() as directory:
            artifacts = pathlib.Path(directory) / 'artifacts'
            artifacts.mkdir()
            (artifacts / 'load-test-report.json').write_text(json.dumps(report), encoding='utf-8')
            return subprocess.run(['node', '--input-type=module', '-e', javascript],
                                  cwd=directory, capture_output=True, text=True, encoding='utf-8', timeout=15)

    def clean(self):
        return {'mode': 'local-read-only', 'target': 'http://127.0.0.1:3000',
                'publicPaths': ['/', '/pricing', '/api/health'],
                'thresholds': {'maxErrorPercent': 1, 'maxP95Ms': 15000},
                'results': [dict(concurrency=n, rounds=3, requests=n*3, successes=n*3,
                                 failed=0, errorPercent=0, elapsedMs=100, requestsPerSecond=n*30,
                                 p50Ms=1, p95Ms=2, p99Ms=3, passed=True) for n in (100, 200)]}

    def test_real_parser_accepts_complete_measured_stages(self):
        self.assertEqual(self.evaluate(self.clean()).returncode, 0)

    def test_rejects_forged_pass_remote_targets_missing_stages_and_changed_budgets(self):
        mutations = [lambda r: r.update(target='https://example.com'),
                     lambda r: r.update(mode='production'),
                     lambda r: r.update(publicPaths=['/admin']),
                     lambda r: r['thresholds'].update(maxP95Ms=15001),
                     lambda r: r['results'].pop(),
                     lambda r: r['results'][0].update(requests=299),
                     lambda r: r['results'][0].update(errorPercent=1),
                     lambda r: r['results'][0].update(p95Ms=16000, p99Ms=17000),
                     lambda r: r['results'][0].update(passed=False),
                     lambda r: r['results'][0].update(p95Ms=None)]
        for mutation in mutations:
            report = copy.deepcopy(self.clean())
            mutation(report)
            with self.subTest(report=report):
                self.assertNotEqual(self.evaluate(report).returncode, 0)

    def test_real_budget_failure_is_not_suppressed(self):
        report = self.clean()
        report['results'][0].update(successes=294, failed=6, errorPercent=2, passed=False)
        self.assertNotEqual(self.evaluate(report).returncode, 0)

    def test_workflow_preserves_isolation_cleanup_failure_and_artifacts(self):
        flow = parse_yaml(ROOT / '.github/workflows/isolated-load-qa.yml')
        self.assertNotIn('secrets', flow['on']['workflow_call'])
        self.assertEqual(flow['jobs']['load']['needs'], 'harness')
        self.assertEqual(flow['jobs']['load']['env']['LOAD_BASE_URL'], 'http://127.0.0.1:3000')
        steps = flow['jobs']['load']['steps']
        benchmark = next(s['run'] for s in steps if s.get('name') == 'Benchmark local public GET routes only')
        for contract in ('rmSync', 'setsid', 'trap cleanup EXIT', 'load_status', 'summary_status', 'kill -KILL'):
            self.assertIn(contract, benchmark)
        artifact = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
        self.assertEqual(artifact['if'], 'always()')
        self.assertEqual(artifact['with']['retention-days'], '14')

    def test_fixture_runs_real_local_http_and_preserves_failure_report(self):
        result = subprocess.run(['node', '--test', 'fixtures/isolated-load/safety.mjs'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
