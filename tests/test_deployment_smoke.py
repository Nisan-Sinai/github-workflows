"""Execute the real URL validator without contacting any deployment."""
import os
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import parse_yaml


class DeploymentSmokeTests(unittest.TestCase):
    def validate_inputs(self, url, command='npm run smoke'):
        workflow = parse_yaml(ROOT / '.github/workflows/deployment-smoke.yml')
        step = next(s for s in workflow['jobs']['smoke']['steps']
                    if s.get('name') == 'Validate deployment inputs')
        javascript = '\n'.join(step['run'].strip().splitlines()[1:-1])
        return subprocess.run(
            ['node', '--input-type=module', '-e', javascript],
            env={**os.environ, 'SITE_URL': url, 'VERIFY_COMMAND': command},
            capture_output=True, text=True, timeout=15,
        )

    def test_accepts_https_without_executing_url_contents(self):
        for url in ('https://example.com', 'https://example.com/path?q=$(false);echo'):
            with self.subTest(url=url):
                self.assertEqual(self.validate_inputs(url).returncode, 0)

    def test_rejects_invalid_insecure_or_credential_bearing_urls(self):
        for url in ('', 'not a URL', 'http://example.com', 'file:///tmp/test',
                    'https://user@example.com', 'https://user:password@example.com'):
            with self.subTest(url=url):
                self.assertNotEqual(self.validate_inputs(url).returncode, 0)

    def test_rejects_missing_or_whitespace_verification(self):
        for command in ('', ' ', '\n\t'):
            with self.subTest(command=command):
                self.assertNotEqual(self.validate_inputs('https://example.com', command).returncode, 0)


class ProductionInputTests(DeploymentSmokeTests):
    def validate_inputs(self, url, command='node verify.mjs', sha='a' * 40):
        workflow = parse_yaml(ROOT / '.github/workflows/production-qa.yml')
        step = next(s for s in workflow['jobs']['production']['steps']
                    if s.get('name') == 'Validate release verification inputs')
        javascript = '\n'.join(step['run'].strip().splitlines()[1:-1])
        return subprocess.run(
            ['node', '--input-type=module', '-e', javascript],
            env={**os.environ, 'PRODUCTION_URL': url, 'VERIFY_COMMAND': command,
                 'EXPECTED_SHA': sha}, capture_output=True, text=True, timeout=15,
        )

    def test_rejects_malformed_https_and_invalid_release_sha(self):
        for url in ('https://', 'https://?x=1'):
            self.assertNotEqual(self.validate_inputs(url).returncode, 0)
        for sha in ('', 'a' * 39, 'a' * 41, 'g' * 40, 'main', 'a' * 40 + '\n'):
            self.assertNotEqual(self.validate_inputs('https://example.com', sha=sha).returncode, 0)
