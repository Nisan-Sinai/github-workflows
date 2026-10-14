#!/usr/bin/env python3
"""Explicitly approved GitHub repository ruleset creation; dry-run by default.

No edits are ever made unless --apply and --confirm match the target repo,
with GITHUB_ADMIN_TOKEN supplied via a secure environment, never in a repo.
Only CREATE is supported; existing rules are never overwritten or deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

OWNER = "Nisan-Sinai"
REPO_PATTERN = re.compile(r"^Nisan-Sinai/[A-Za-z0-9_.-]+$")
ALLOWED_RULES = {"deletion", "non_fast_forward", "required_linear_history", "pull_request", "required_status_checks"}


def validate(repo: str, data: dict) -> dict:
    if not REPO_PATTERN.fullmatch(repo):
        raise ValueError(f"Only explicitly owned {OWNER}/<repo> repositories are supported")
    if not isinstance(data, dict) or data.get("target") != "branch" or data.get("enforcement") != "active":
        raise ValueError("Only active branch rulesets are supported")
    if not isinstance(data.get("name"), str) or not data["name"].strip():
        raise ValueError("Ruleset needs a name")
    if data.get("bypass_actors") != []:
        raise ValueError("Ruleset must have no bypass actors")
    refs = data.get("conditions", {}).get("ref_name", {})
    inc, exc = refs.get("include"), refs.get("exclude")
    if not isinstance(inc, list) or len(inc) != 1 or not isinstance(inc[0], str) or not inc[0].startswith("refs/heads/") or exc != []:
        raise ValueError("Expected exactly one named branch and no exclusions")
    branch = inc[0].removeprefix("refs/heads/")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch):
        raise ValueError("Unsafe branch name")
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules or any(not isinstance(r, dict) or r.get("type") not in ALLOWED_RULES for r in rules):
        raise ValueError("Unknown or empty rules")
    types = [r["type"] for r in rules]
    required = {"deletion", "non_fast_forward", "pull_request", "required_status_checks"}
    if not required.issubset(types) or len(types) != len(set(types)):
        raise ValueError("Missing or duplicate essential protection rules")
    checks = next(r for r in rules if r["type"] == "required_status_checks").get("parameters", {}).get("required_status_checks")
    if not isinstance(checks, list) or not checks or any(not isinstance(x.get("context"), str) or not x["context"] for x in checks):
        raise ValueError("Required status checks must not be empty")
    return {"repo": repo, "branch": branch, "name": data["name"], "required_checks": [x["context"] for x in checks]}


def api(repo: str, token: str, method: str = "GET", payload: dict | None = None):
    url = f"https://api.github.com/repos/{repo}/rulesets"
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request = urllib.request.Request(url, data=body, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Nisan-Sinai-ruleset-admin/1.0",
        **({"Content-Type": "application/json"} if body is not None else {}),
    })
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not print headers or error bodies containing potentially sensitive info.
        raise RuntimeError(f"GitHub API returned HTTP {error.code} ({method}); check repository admin rights") from error


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo", required=True, help="Nisan-Sinai/repository")
    cli.add_argument("--file", required=True, help="locally reviewed ruleset JSON file")
    cli.add_argument("--apply", action="store_true", help="opt in to an admin write (otherwise offline dry-run)")
    cli.add_argument("--confirm", help="must exactly match --repo to permit writing")
    args = cli.parse_args()
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    plan = validate(args.repo, data)
    # JSON escapes keep dry-run output safe on non-UTF-8 Windows consoles.
    print(json.dumps({"mode": "APPLY" if args.apply else "DRY RUN", **plan}, indent=2))
    if not args.apply:
        print("No network calls or changes made; use --apply --confirm <full repo> for an explicitly authorized change.")
        return
    if args.confirm != args.repo:
        cli.error("--confirm must exactly match --repo")
    token = os.environ.get("GITHUB_ADMIN_TOKEN")
    if not token:
        cli.error("GITHUB_ADMIN_TOKEN with administration permission must be set securely")
    current = api(args.repo, token)
    if any(x.get("name") == data["name"] for x in current):
        cli.error("Ruleset with this name already exists; refusing to overwrite")
    created = api(args.repo, token, method="POST", payload=data)
    if created.get("id") is None:
        raise RuntimeError("GitHub response did not confirm a created ruleset")
    print(f"Ruleset created (id={created['id']}) in {args.repo}; verify actual branch enforcement in GitHub Settings.")


if __name__ == "__main__":
    main()
