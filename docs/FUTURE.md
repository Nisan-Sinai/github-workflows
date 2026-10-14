# Future-proofing and maintenance

This hub is **not a one-size-fits-all pipeline**. It is a library of opt-in verification components plus branch policy templates.

- New `npm`/`pnpm`/`yarn`/`bun` JS project: use `node-ci.yml` and explicit lockfile-aware commands.
- New Python service: use `python-ci.yml` and specify its install/test commands.
- New .NET app: use `dotnet-ci.yml`, set framework version and runner suitable for the target, and select an actual solution/project file.
- Supabase, MongoDB, GraphQL, E2E, accessibility, Cloudflare, Vercel, and cross-service integration tests: keep domain-specific consumer jobs **until dedicated reusable workflows exist and are validated**.
- For more languages/frameworks: add a new reusable workflow, fixture, unit validation and versioned usage examples in a PR. Never silently change consumer configurations.
- At least weekly: run the read-only public inventory and inspect drift.
- Every dependency update: use reviewed PRs; don't auto-merge major versions solely because CI happens to pass.
- Consider a private administration-only repo for cross-repository write automation, with a **GitHub App installation scoped to selected repositories** rather than a personal token, human approvals, audit trail and an explicit per-repo allowlist. That is a *future optional extension*, not enabled here.
