"""Contract tests: prevent missing required gates and unsafe config regressions."""
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import REUSABLE, parse_yaml, validate


def flow(name):
    return parse_yaml(ROOT / '.github/workflows' / name)


class ReusableWorkflowContractTests(unittest.TestCase):
    def test_catalog_and_full_hub_contracts(self):
        validate()

    def test_all_reusable_workflows_are_opt_in_only(self):
        for name in REUSABLE:
            with self.subTest(name=name):
                self.assertEqual(list(flow(name)['on']), ['workflow_call'])

    def test_immutable_caller_examples(self):
        for path in (ROOT / 'examples').glob('*.example'):
            with self.subTest(name=path.name):
                text = path.read_text()
                self.assertNotIn('@main', text)
                self.assertNotIn('@master', text)

    def test_browser_e2e_mandatory(self):
        f = flow('browser-qa.yml')
        inputs = f['on']['workflow_call']['inputs']
        self.assertEqual(inputs['e2e-command']['required'], 'true')
        self.assertEqual(inputs['build-command']['required'], 'true')
        self.assertEqual(inputs['browser-install-command']['required'], 'true')
        self.assertIn('Playwright E2E and accessibility', [x.get('name') for x in f['jobs']['browser']['steps']])

    def test_coverage_and_bundle_security_configurable(self):
        inputs = flow('advanced-node-qa.yml')['on']['workflow_call']['inputs']
        self.assertEqual(inputs['coverage-command']['required'], 'true')
        for name in ('format-command', 'bundle-security-command', 'deadcode-command', 'source-secret-scan-command'):
            self.assertIn(name, inputs)

    def test_supabase_requires_real_checks(self):
        inputs = flow('supabase-qa.yml')['on']['workflow_call']['inputs']
        for key in ('schema-drift-command', 'integration-command', 'rls-command'):
            with self.subTest(input=key):
                self.assertEqual(inputs[key]['required'], 'true')
        steps = [s.get('name') for s in flow('supabase-qa.yml')['jobs']['integration']['steps']]
        self.assertIn('Start fresh Supabase and apply migrations', steps)
        self.assertIn('Shut down test database', steps)

    def test_security_history_audit_and_strict_watch(self):
        f = flow('security-ci.yml')
        steps = f['jobs']['secrets']['steps']
        self.assertTrue(any(s.get('with', {}).get('fetch-depth') == '0' for s in steps))
        deps = flow('dependency-watch.yml')['on']['workflow_call']['inputs']
        self.assertEqual(deps['audit-command']['required'], 'true')

    def test_dependency_automation_is_dry_run_by_default(self):
        f = flow('dependabot-automerge.yml')
        self.assertEqual(f['on']['workflow_call']['inputs']['enable-merge']['default'], 'false')
        self.assertEqual(f['permissions']['contents'], 'write')
        self.assertNotIn('pull_request_target', f['on'])

    def test_production_needs_expected_release_sha(self):
        f = flow('production-qa.yml')
        inputs = f['on']['workflow_call']['inputs']
        for name in ('production-url', 'expected-sha', 'verify-command'):
            self.assertEqual(inputs[name]['required'], 'true')

    def test_vercel_checks_exact_head_and_sender(self):
        content = (ROOT / '.github/workflows/vercel-gate.yml').read_text()
        self.assertIn('github.event.pull_request.head.sha', content)
        self.assertIn('vercel[bot]', content)
        self.assertIn('success', content)

    def test_preview_deployment_opt_in_and_verified(self):
        f = flow('vercel-preview-deployment.yml')
        self.assertEqual(f['permissions']['deployments'], 'write')
        content = (ROOT / '.github/workflows/vercel-preview-deployment.yml').read_text()
        self.assertIn('vercel[bot]', content)
        self.assertIn('environment: "Preview"', content)
        self.assertIn('github.event.pull_request.head.sha', content)

    def test_public_registry_contains_no_private_names(self):
        d = json.loads((ROOT / 'policies/public-repositories.json').read_text())
        names = {r['name'] for r in d['repositories']}
        self.assertNotIn('shel-yah-store', names)
        self.assertNotIn('cash-flow-navigator', names)
        self.assertNotIn('-', names)

    def test_read_only_public_inventory(self):
        f = flow('inventory.yml')
        self.assertEqual(f['permissions']['contents'], 'read')
        self.assertIn('schedule', f['on'])
        self.assertNotIn('pull_request_target', f['on'])

    def test_no_workflow_checkout_tokens(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            with self.subTest(path=path.name):
                for job in flow(path.name)['jobs'].values():
                    for step in job.get('steps', []):
                        if step.get('uses', '').startswith('actions/checkout@'):
                            self.assertEqual(step.get('with', {}).get('persist-credentials'), 'false')


if __name__ == '__main__':
    unittest.main()
