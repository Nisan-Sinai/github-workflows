"""The database gate must reject empty commands and only provision a local service."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import parse_yaml
BASH = shutil.which('bash')


class PostgresContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = parse_yaml(ROOT / '.github/workflows/postgres-contract.yml')
        cls.job = cls.workflow['jobs']['contract']

    def test_database_is_isolated_and_requires_an_explicit_contract(self):
        inputs = self.workflow['on']['workflow_call']['inputs']
        self.assertEqual(inputs['verify-command']['required'], 'true')
        self.assertNotIn('database-url', inputs)
        self.assertNotIn('secrets', self.workflow['on']['workflow_call'])
        self.assertEqual(
            self.job['env']['DATABASE_URL'],
            'postgres://postgres:postgres@127.0.0.1:5432/postgres',
        )
        self.assertRegex(self.job['services']['postgres']['image'], r'^postgres:17@sha256:[0-9a-f]{64}$')
        self.assertEqual(self.job['timeout-minutes'], '15')

    @unittest.skipUnless(BASH, 'Bash is required to execute workflow command guards')
    def test_empty_and_whitespace_only_commands_fail_closed(self):
        guard = next(step for step in self.job['steps']
                     if step.get('name') == 'Require a database contract command')['run']
        for command in ('', ' ', '\n\t'):
            with self.subTest(command=repr(command)):
                result = subprocess.run(
                    [BASH, '-euo', 'pipefail', '-c', guard],
                    env={**os.environ, 'VERIFY': command},
                    capture_output=True, text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('verify-command must not be blank', result.stdout)

    @unittest.skipUnless(BASH, 'Bash is required to execute workflow command guards')
    def test_nonempty_command_passes_validation_without_being_executed(self):
        guard = next(step for step in self.job['steps']
                     if step.get('name') == 'Require a database contract command')['run']
        result = subprocess.run(
            [BASH, '-euo', 'pipefail', '-c', guard],
            env={**os.environ, 'VERIFY': 'exit 99'},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
