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
