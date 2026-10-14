# Adoption plan for 12 personal repositories verified 2026-10-14

**No repository has been modified by this starter kit.** Introduce shared workflows only after a review of the existing stack/scripts and by individual PR. The public registry lists 10 public repos; the remaining 2 are private and intentionally NOT recorded here.

| Public repository | Default branch | Proposed CI profile | Approach |
|---|---|---|---|
| AccountManagement | master | dotnet-legacy | Check framework/Windows dependencies before enabling |
| super-shop-nisan | main | node-legacy | Audit scripts and build/test availability |
| netflix-nisan-sinai | main | node-legacy | Audit scripts and build/test availability |
| nisan-project-site | master | node-legacy | Audit scripts and build/test availability |
| test-winter-86-nisan-sinai | main | node-legacy | Audit scripts and build/test availability |
| LD-Event-Design | main | node-npm | **Preserve current CI, e2e, Vercel, Supabase and existing auto-merge** |
| arrival-confirmations | main | node-pnpm | **Preserve current CI, RLS, 50-event tests, Vercel and existing auto-merge** |
| nisan-sinai-technologies | main | node-npm | **Preserve current CI**; activate the separately prepared ruleset using admin Settings |
| harel-ai-claims-copilot | main | node-npm | Inspect coverage and provider test dependencies |
| artzi-energy | main | node-npm | **Preserve `quality`, `performance`, Vercel** |

**Two additional private repositories:** onboard privately with an explicit `--preset`, based on their actual source and default branch. Do not add them by name to this public hub. One private monorepo has `dev` as its default and already has a strict `verify` + both Vercel deployments (after PR #58); preserve that check exactly and do not remove it.

## Safe migration

1. Discover and document exact protected branch, status checks, package manager, CI commands, deployment projects and required review rules.
2. Introduce shared jobs in a new PR. Full pinned SHA. Existing CI remains on and stays required.
3. Verify the new shared jobs in a live PR and re-run if flakiness occurs; do not bypass failing checks.
4. If replacing duplicate jobs, change protection only once the new contexts appear and pass. Test with an empty commit PR and ensure stale/red checks block merging.
5. Capture revert instructions and actual branch rule state.
6. Record the latest proven SHA of the central hub; upgrade consumer pins by PR only.

Each repo is independent. Do not assume all Node repos support a `lint` script or all legacy C# repos can build on a Linux runner.

## Shared Dependabot automation — only after explicit opt-in

The reusable workflow `.github/workflows/dependabot-automerge.yml` contains a strict fail-closed Patch/Minor merge gate. **It does not run automatically simply because this hub exists** and defaults to a no-write dry run. A consumer owner must deliberately add a trusted `pull_request_target` caller pinned to a hub SHA, list exact required check/status names, grant the limited workflow write permissions, and explicitly turn on `enable-merge: true` in a reviewed PR. The bot refuses major/unknown updates, stale heads, behind/conflicted branches, missing/pending/failing checks and failing Vercel statuses. GitHub merge rules still apply.

**Do not add this caller** to a consumer that already has Dependabot auto-merge without first checking for duplicate or racing merger workflows. A trial should use `enable-merge: false`, then require real green preview/CI before opting in to writes. See `examples/dependabot-caller.yml.example`.
