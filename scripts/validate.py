#!/usr/bin/env python3
"""No-secrets validation of catalog, presets, and reusable workflows."""
import json
import re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"
CALLABLE = ["node-ci.yml", "python-ci.yml", "dotnet-ci.yml", "security-ci.yml", "vercel-gate.yml", "dependabot-eligibility.yml", "dependabot-automerge.yml"]


def validate() -> None:
    data = json.loads((ROOT / "policies/public-repositories.json").read_text())
    presets = json.loads((ROOT / "policies/presets.json").read_text())
    assert data["owner"] == "Nisan-Sinai"
    assert len(data["repositories"]) == 10
    assert len({r["name"] for r in data["repositories"]}) == len(data["repositories"])
    for r in data["repositories"]:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+", r["name"])
        assert re.fullmatch(r"[A-Za-z0-9._/-]+", r["branch"])
        assert r["profile"] in presets
        assert r["adoption"] in ("assess", "preserve-existing-ci", "opt-in")
    for path in WORKFLOWS.glob("*.yml"):
        # BaseLoader avoids YAML 1.1 parsing the YAML key `on` as Boolean True.
        flow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        assert isinstance(flow, dict), path
        assert "jobs" in flow and "on" in flow, path
        if path.name in CALLABLE:
            assert "workflow_call" in flow["on"], path
        else:
            assert "workflow_call" not in flow["on"], path
        if path.name == "dependabot-automerge.yml":
            assert flow.get("permissions", {}).get("contents") == "write", path
            assert flow.get("permissions", {}).get("pull-requests") == "write", path
            assert "pull_request_target" not in flow["on"], path
            assert flow["on"]["workflow_call"]["inputs"]["enable-merge"]["default"] == "false", path
        else:
            assert flow.get("permissions", {}).get("contents") == "read", path
    for name in CALLABLE:
        assert (WORKFLOWS / name).is_file()
    assert not any(p.startswith("Nisan-Sinai/") for p in data.keys())
    print(f"Validated {len(list(WORKFLOWS.glob('*.yml')))} workflow YAML files and "
          f"{len(data['repositories'])} public catalog records")


if __name__ == "__main__":
    validate()
