# Future-proofing and maintenance

This hub is **not a one-size-fits-all pipeline**. It is a library of opt-in verification components plus branch policy templates.

## Private and newly created repositories

Keep this hub public and adopt it from each private repository with a private PR. The caller should pin a reviewed 40-character hub commit SHA; never register the private repository name, commands, URLs, or secrets in this public hub.

For any new repository, select a preset explicitly and generate a draft caller without adding the repository to the public catalog:

```bash
python scripts/generate_consumer.py \
  --repo Nisan-Sinai/<private-or-new-repository> \
  --sha <approved-40-character-hub-sha> \
  --preset node-npm
```

Review the generated commands against that repository before merging. Connecting one repository does not automatically connect future repositories, and updating the hub does not silently update consumers because callers are SHA-pinned. Upgrade each caller by reviewed PR. If cross-repository onboarding is automated later, keep the repository inventory and execution in a private administration repository backed by a narrowly scoped GitHub App and an explicit allowlist.

- New `npm`/`pnpm`/`yarn`/`bun` JS project: use `node-ci.yml` and explicit lockfile-aware commands.
- New Python service: use `python-ci.yml` and specify its install/test commands.
- New .NET app: use `dotnet-ci.yml`, set framework version and runner suitable for the target, and select an actual solution/project file.
- Supabase, browser E2E/accessibility, Vercel and production verification can use the dedicated gates in this hub after a real consumer proves them green. Keep MongoDB, GraphQL, Cloudflare and other domain-specific consumer jobs until dedicated reusable workflows exist and are validated.
- For more languages/frameworks: add a new reusable workflow, fixture, unit validation and versioned usage examples in a PR. Never silently change consumer configurations.
- At least weekly: run the read-only public inventory and inspect drift.
- Every dependency update: use reviewed PRs; don't auto-merge major versions solely because CI happens to pass.
- Consider a private administration-only repo for cross-repository write automation, with a **GitHub App installation scoped to selected repositories** rather than a personal token, human approvals, audit trail and an explicit per-repo allowlist. That is a *future optional extension*, not enabled here.
