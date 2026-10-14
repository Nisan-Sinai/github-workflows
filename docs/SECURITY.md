# Security model

- Central workflows run in the **consumer's** repository context. The reusable workflow repository cannot see or administer consumer repositories merely because it stores a YAML file.
- Opt-in consumer PRs with a **full 40-character commit SHA** prevent unexpected updates to consumers if hub `main` changes.
- All reusable workflows request minimal read permissions; there is no privileged checkout of PR content, no administrative write token, no branch setting changes, and no remote execution through third-party PR content.
- Dependabot has a **read-only eligibility** workflow and a separate **dry-run-by-default opt-in auto-merge** workflow. The opt-in workflow needs an explicitly approved `pull_request_target` caller and pull-request write permission; it never checks out PR code, rejects major versions, validates all mandatory statuses and exact SHA, and never overrides branch rules. Existing reviewed repo-local auto-merge stays authoritative until separately approved migration.
- Branch ruleset generation is local/offline and **not enforced** until explicitly imported and applied in GitHub Settings.
- A public central repository must never contain private repository names, tokens, secrets, URLs with access credentials, environment files, Supabase secrets, Vercel tokens, or private organizational context.
- Repository-specific Vercel statuses vary. The reusable Vercel gate validates a status from `vercel[bot]` with a `vercel.com` link on the exact PR HEAD, but cannot guarantee a deployment is functionally healthy; keep tests and first-party branch protection.
- Gitleaks uses its published GitHub Action; check its licensing/availability in private repositories. If a private repository requires a paid license, choose another supported scanner rather than weakening security checks.
- Run repository access audits after an integration is installed; don't make `GH_TOKEN` public or print authorization headers.
- The drift inventory intentionally audits only the **public** registry and never writes changes.

## Deep QA controls

- `Hub guard` now runs `actionlint` (fixed release version **and** verified archive SHA-256) on the full `.github/workflows` tree; 20 original policy tests plus simulated GitHub API misuse cases run on every PR.
- Third-party GitHub Actions are pinned to exact immutable **40-character commit hashes**, not mutable `@v4` tags. The code-level validation rejects new unpinned actions and `continue-on-error: true` in all reusable gates.
- Dependabot is dry-run by default. Opt-in merging waits for *all* check runs on the precise PR head to finish, including newly added/unlisted checks, and refuses failures. Fake API tests assert that unknown pending checks cannot be outrun.
- Reusable Vercel gates fail rather than silently produce a skipped/green job when invoked by an unsupported event or an untrusted fork.
- `main` branch protection is a **separate GitHub administrator operation**: a green guard never implies that rulesets are activated. Check GitHub Settings → Rules before relying on the repo as your CI trust anchor.
- Actionlint validates workflow syntax; these static tests and simulated API responses are not a substitute for running every reusable workflow against a real consumer PR. Every migration must be opt-in with a pinned hub SHA and its own end-to-end green run.
