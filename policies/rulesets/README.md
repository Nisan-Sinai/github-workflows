# Branch policies

Use `scripts/render_ruleset.py` to generate an importable ruleset with explicitly named required checks for a **specific repository and branch**.

- `main`: production branches, usually full CI + Vercel.
- `dev`: development branches, usually CI + both project-specific Vercel statuses if applicable.
- `master`: older repositories, after framework-specific checks have been verified.

Rulesets cannot be activated simply by committing JSON. See `docs/BRANCH-PROTECTION.md`.
