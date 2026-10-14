#!/usr/bin/env python3
"""Render a per-repo branch ruleset for ADMIN REVIEW; DOES NOT activate it."""
import argparse
import json
import re
from pathlib import Path


def create(branch: str, checks: list[str], strict: bool = False) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or branch.startswith("-"):
        raise ValueError("Unsafe branch")
    names = [c.strip() for c in checks]
    if not names or any(not n for n in names) or len(set(names)) != len(names):
        raise ValueError("Pass a nonempty, duplicate-free list of real check names")
    return {
        "name": f"Protect {branch} – audited checks",
        "target": "branch", "enforcement": "active", "bypass_actors": [],
        "conditions": {"ref_name": {"include": [f"refs/heads/{branch}"], "exclude": []}},
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "required_linear_history"},
            {"type": "pull_request", "parameters": {
                "required_approving_review_count": 0, "require_code_owner_review": False,
                "dismiss_stale_reviews_on_push": False, "require_last_push_approval": False,
                "required_review_thread_resolution": True,
                "allowed_merge_methods": ["squash"]}},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": strict,
                "required_status_checks": [{"context": n} for n in names]}}
        ]
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--branch", required=True)
    p.add_argument("--checks", required=True, nargs="+", help="Exact current check/status names")
    p.add_argument("--strict", action="store_true", help="Require up-to-date branch")
    p.add_argument("--output", help="Local path, if omitted prints the ruleset")
    args = p.parse_args()
    value = json.dumps(create(args.branch, args.checks, args.strict), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        path = Path(args.output)
        if path.exists():
            p.error("Will not overwrite an existing ruleset")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        print(path)
    else:
        print(value, end="")


if __name__ == "__main__":
    main()
