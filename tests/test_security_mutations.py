"""Negative tests proving hub policy fails closed when controls are weakened."""
import json
import re
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate as catalog_validator
from render_ruleset import create
from admin_ruleset import validate as validate_admin


class WorkflowMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / '.github/workflows', self.root / '.github/workflows')
        shutil.copytree(ROOT / 'policies', self.root / 'policies')
        shutil.copytree(ROOT / 'renovate', self.root / 'renovate')
        shutil.copy2(ROOT / 'default.json', self.root / 'default.json')
        self.mock_root = patch.object(catalog_validator, 'ROOT', self.root)
        self.mock_workflows = patch.object(catalog_validator, 'WORKFLOWS', self.root / '.github/workflows')
        self.mock_root.start()
        self.mock_workflows.start()
        self.addCleanup(self.mock_root.stop)
        self.addCleanup(self.mock_workflows.stop)

    def change(self, filename, original, replacement):
        target = self.root / '.github/workflows' / filename
        before = target.read_text()
        self.assertIn(original, before)
        target.write_text(before.replace(original, replacement, 1))

    def test_pristine_policy_passes(self):
        catalog_validator.validate()

    def test_floating_checkout_action_is_rejected(self):
        target = self.root / '.github/workflows/guard.yml'
        before = target.read_text()
        after, replacements = re.subn(
            r'actions/checkout@[0-9a-f]{40}', 'actions/checkout@v7', before, count=1)
        self.assertEqual(replacements, 1)
        target.write_text(after)
        with self.assertRaisesRegex(ValueError, 'immutable 40-character'):
            catalog_validator.validate()

    def test_suppressed_failure_is_rejected(self):
        self.change('guard.yml', '      - name: Python syntax',
                    '      - name: Python syntax\n        continue-on-error: true')
        with self.assertRaisesRegex(ValueError, 'failure suppression'):
            catalog_validator.validate()

    def test_checkout_token_persistence_is_rejected(self):
        self.change('guard.yml', 'persist-credentials: false', 'persist-credentials: true')
        with self.assertRaisesRegex(ValueError, 'credential persistence'):
            catalog_validator.validate()

    def test_privileged_trigger_is_rejected(self):
        self.change('guard.yml', '  pull_request:', '  pull_request_target:')
        with self.assertRaisesRegex(ValueError, 'unexpected trigger'):
            catalog_validator.validate()

    def test_shallow_secret_history_is_rejected(self):
        self.change('security-ci.yml', 'fetch-depth: 0', 'fetch-depth: 1')
        with self.assertRaisesRegex(ValueError, 'complete Git history'):
            catalog_validator.validate()

    def test_range_only_secret_scan_is_rejected(self):
        self.change('security-ci.yml',
                    'gitleaks git --redact --verbose .',
                    'gitleaks git --redact --verbose --log-opts=-1 .')
        with self.assertRaisesRegex(ValueError, 'complete Git history with redaction'):
            catalog_validator.validate()

    def test_unredacted_secret_output_is_rejected(self):
        self.change('security-ci.yml',
                    'gitleaks git --redact --verbose .',
                    'gitleaks git --verbose .')
        with self.assertRaisesRegex(ValueError, 'complete Git history with redaction'):
            catalog_validator.validate()

    def test_platform_automerge_cannot_bypass_test_evaluation(self):
        target = self.root / 'default.json'
        policy = json.loads(target.read_text())
        policy['platformAutomerge'] = True
        target.write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, 'evaluate checks itself'):
            catalog_validator.validate()

    def test_automatic_updates_cannot_ignore_tests(self):
        target = self.root / 'default.json'
        policy = json.loads(target.read_text())
        rule = next(rule for rule in policy['packageRules'] if rule.get('automerge'))
        rule['ignoreTests'] = True
        target.write_text(json.dumps(policy))
        with self.assertRaisesRegex(ValueError, 'wait for repository checks'):
            catalog_validator.validate()

    def test_hidden_new_reusable_workflow_must_be_registered(self):
        (self.root / '.github/workflows/unreviewed.yml').write_text(
            'name: new\non:\n  workflow_call:\npermissions:\n  contents: read\njobs:\n  x:\n    runs-on: ubuntu-latest\n    timeout-minutes: 5\n    steps:\n      - run: echo hi\n')
        with self.assertRaisesRegex(ValueError, 'Unexpected/missing workflow'):
            catalog_validator.validate()


class AdminSafetyMutationTests(unittest.TestCase):
    def test_ruleset_rejects_unknown_account_and_bypass(self):
        rules = create('main', ['Hub / validate'], strict=True)
        self.assertEqual(validate_admin('Nisan-Sinai/github-workflows', rules)['branch'], 'main')
        with self.assertRaises(ValueError):
            validate_admin('smartfin-ai/github-workflows', rules)
        rules['bypass_actors'].append({'actor_id': 1, 'actor_type': 'OrganizationAdmin'})
        with self.assertRaises(ValueError):
            validate_admin('Nisan-Sinai/github-workflows', rules)

    def test_ruleset_rejects_unprotected_branch_and_empty_checks(self):
        with self.assertRaises(ValueError):
            create('main', [])
        rules = create('dev', ['Hub / validate'], strict=True)
        rules['conditions']['ref_name']['include'] = ['refs/heads/*']
        with self.assertRaises(ValueError):
            validate_admin('Nisan-Sinai/github-workflows', rules)


if __name__ == '__main__':
    unittest.main()
