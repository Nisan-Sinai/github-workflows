import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from generate_consumer import workflow
from render_ruleset import create

SHA = "0123456789abcdef0123456789abcdef01234567"


class GovernanceTests(unittest.TestCase):
    def test_registered_public_only(self):
        data = json.loads((ROOT / "policies/public-repositories.json").read_text())
        self.assertEqual(len(data["repositories"]), 10)
        self.assertEqual(data["owner"], "Nisan-Sinai")
        names = {r["name"] for r in data["repositories"]}
        self.assertEqual(len(names), 10)
        self.assertEqual(names, {
            "AccountManagement", "super-shop-nisan", "netflix-nisan-sinai",
            "nisan-project-site", "test-winter-86-nisan-sinai", "LD-Event-Design",
            "arrival-confirmations", "nisan-sinai-technologies",
            "harel-ai-claims-copilot", "artzi-energy",
        })

    def test_consumer_immutable_sha(self):
        result = workflow("Nisan-Sinai/artzi-energy", SHA, "node-npm")
        self.assertIn(f"node-ci.yml@{SHA}", result)
        self.assertIn("pull_request:", result)
        self.assertNotIn("@main", result)
        with self.assertRaises(ValueError):
            workflow("Nisan-Sinai/artzi-energy", "main", "node-npm")

    def test_consumer_for_dotnet(self):
        result = workflow("Nisan-Sinai/AccountManagement", SHA, "dotnet-legacy")
        self.assertIn("dotnet-ci.yml@", result)
        self.assertIn("windows-latest", result)

    def test_consumers_not_cross_account(self):
        with self.assertRaises(ValueError):
            workflow("smartfin-ai/other", SHA, "node-npm")

    def test_ruleset_specific_and_fail_closed(self):
        x = create("dev", ["verify", "Vercel – my-web"], strict=True)
        self.assertEqual(x["conditions"]["ref_name"]["include"], ["refs/heads/dev"])
        self.assertEqual(x["enforcement"], "active")
        self.assertEqual(x["bypass_actors"], [])
        self.assertTrue(x["rules"][-1]["parameters"]["strict_required_status_checks_policy"])
        self.assertIn({"type": "non_fast_forward"}, x["rules"])
        with self.assertRaises(ValueError):
            create("main", [])
        with self.assertRaises(ValueError):
            create("main", ["CI", "CI"])


if __name__ == "__main__":
    unittest.main()


class AdminSafetyTests(unittest.TestCase):
    def test_admin_ruleset_scope_and_guard(self):
        from admin_ruleset import validate
        x = create('main', ['CI', 'Vercel'], strict=True)
        plan = validate('Nisan-Sinai/example', x)
        self.assertEqual(plan['branch'], 'main')
        self.assertEqual(plan['required_checks'], ['CI', 'Vercel'])
        with self.assertRaises(ValueError):
            validate('smartfin-ai/example', x)
        x['bypass_actors'] = [{'actor_id': 1}]
        with self.assertRaises(ValueError):
            validate('Nisan-Sinai/example', x)
