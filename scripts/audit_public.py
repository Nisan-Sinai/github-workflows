#!/usr/bin/env python3
"""Read-only GitHub policy inventory for explicitly public repos only.

Do not add private repository metadata: workflow logs and summaries may be public.
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]
TOKEN = os.getenv("GH_TOKEN", "")


def get(path: str):
    req = urllib.request.Request(BASE + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "nisan-sinai-policy-audit/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response), None
    except urllib.error.HTTPError as error:
        return None, f"HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        return None, f"{type(error).__name__}"


def audit(entry: dict, owner: str) -> dict:
    repo = entry["name"]
    branch = entry["branch"]
    endpoint = f"/repos/{owner}/{repo}"
    response = {"repository": f"{owner}/{repo}", "expected_branch": branch}
    info, error = get(endpoint)
    if error:
        return {**response, "error": error}
    # Public repo registry is a hard safety boundary, not an API search.
    if info.get("private") is not False:
        return {**response, "error": "Refusing non-public repository"}
    b, e = get(f"{endpoint}/branches/{branch}")
    response["protected"] = bool(b.get("protected")) if b else None
    response["branch_error"] = e
    _, e = get(f"{endpoint}/contents/.github/dependabot.yml")
    response["dependabot"] = e is None
    r, e = get(f"{endpoint}/rulesets")
    response["active_rulesets"] = len([x for x in r if x.get("enforcement") == "active"]) if isinstance(r, list) else None
    response["ruleset_error"] = e
    return response


def main() -> None:
    catalog = json.loads((ROOT / "policies/public-repositories.json").read_text())
    rows = [audit(entry, catalog["owner"]) for entry in catalog["repositories"]]
    lines = ["# Public repository policy drift report", "",
             "*Read-only snapshot; missing permissions or GitHub errors are reported as unknown.*", "",
             "| Public repository | Target | Protected | Dependabot | Active rulesets |",
             "|---|---|---|---|---:|"]
    for r in rows:
        mark = lambda x: "Unknown" if x is None else ("Yes" if x else "No")
        lines.append(f"| {r['repository']} | `{r['expected_branch']}` | {mark(r.get('protected'))} | "
                     f"{mark(r.get('dependabot')) if not r.get('error') else 'Unknown'} | "
                     f"{r.get('active_rulesets') if r.get('active_rulesets') is not None else 'Unknown'} |")
        if r.get("error") or r.get("branch_error") or r.get("ruleset_error"):
            print(f"::warning::{r['repository']}: {r.get('error') or r.get('branch_error') or r.get('ruleset_error')}")
    report = "\n".join(lines) + "\n"
    print(report)
    if path := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(path, "a", encoding="utf-8") as f:
            f.write(report)
    # Deliberately no write API requests, no issues/PRs, no external posting.


if __name__ == "__main__":
    main()
