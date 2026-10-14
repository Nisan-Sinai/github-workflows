#!/usr/bin/env python3
"""Generate a **draft only** reusable workflow caller from an approved preset.

No GitHub operations. Always inspect package.json/CI first.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = re.compile(r"^[0-9a-fA-F]{40}$")
REPO = re.compile(r"^Nisan-Sinai/[A-Za-z0-9_.-]+$")


def workflow(repo: str, sha: str, preset: str) -> str:
    if not REPO.fullmatch(repo):
        raise ValueError("Repository must be Nisan-Sinai/<repository> (personal account)")
    if not SHA.fullmatch(sha):
        raise ValueError("Use a real 40-character immutable Git commit SHA")
    profiles = json.loads((ROOT / "policies/presets.json").read_text())
    if preset not in profiles:
        raise ValueError(f"Unknown preset {preset!r}; choose {', '.join(profiles)}")
    entry = profiles[preset]
    if entry["workflow"] not in {"node-ci.yml", "python-ci.yml", "dotnet-ci.yml"}:
        raise ValueError("Unexpected unapproved reusable workflow")

    # The caller owns triggering branches and all stack-specific command decisions.
    fields = ["name: Shared CI (opt-in)", "on:", "  pull_request:", "  workflow_dispatch:",
              "permissions:", "  contents: read", "jobs:", "  shared:",
              f"    uses: Nisan-Sinai/github-workflows/.github/workflows/{entry['workflow']}@{sha.lower()}",
              "    with:"]
    for key, value in entry.items():
        if key == "workflow":
            continue
        if isinstance(value, bool):
            rendered = str(value).lower()
        else:
            rendered = json.dumps(value, ensure_ascii=False)
        fields.append(f"      {key}: {rendered}")
    fields += ["", "# IMPORTANT: tailor commands/SDK versions to this consumer before merge.",
               "# Keep existing CI, Vercel and required status checks until the shared job is proven green."]
    return "\n".join(fields) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True)
    p.add_argument("--sha", required=True)
    p.add_argument("--preset", default=None)
    p.add_argument("--output", default=None, help="Optional local file; otherwise print only")
    a = p.parse_args()
    public = json.loads((ROOT / "policies/public-repositories.json").read_text())
    match = next((r for r in public["repositories"] if f"Nisan-Sinai/{r['name']}" == a.repo), None)
    preset = a.preset or (match["profile"] if match else None)
    if not preset:
        p.error("Private/new repo: supply --preset (its name will not be registered publicly)")
    try:
        out = workflow(a.repo, a.sha, preset)
    except ValueError as e:
        p.error(str(e))
    if a.output:
        path = Path(a.output)
        if path.exists():
            p.error(f"Refusing to overwrite {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(out)
        print(f"Created local draft: {path}")
    else:
        print(out, end="")


if __name__ == "__main__":
    main()
