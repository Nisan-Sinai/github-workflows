# Nisan-Sinai / github-workflows

> A centralized, **opt-in** control plane for GitHub Actions, security policy, and onboarding of Nisan-Sinai repositories (personal account, **no Organization needed**).

[![Policy CI](https://img.shields.io/badge/policy-read--only-blue)](#principles) [![Adoption](https://img.shields.io/badge/adoption-PR--by--PR-brightgreen)](#adoption)

## Principles

1. **One source, multiple stacks:** reusable Node (npm/pnpm/yarn/bun), Python and .NET CI plus a separate security workflow.
2. **Never silently replace existing checks.** New workflows are **additive** until their checks are verified and branch rules have been migrated by a repository administrator.
3. **Safe-by-default:** no credentials, repository-admin token, remote code execution via `pull_request_target`, unattended bulk edits, or automatic rule changes.
4. **Immutable consumers:** use a **full 40-character SHA**, not `@main`, for shared workflows. Upgrade by PR in each consumer.
5. **Drift monitoring:** public-repository inventory audit reports protection, Dependabot and Actions configuration but **never mutates** settings.
6. **Public/private separation:** this hub stays **public** so both public and private consumer repositories can call it. Do **not** commit private repository names, secrets, tokens, sensitive inventories, or internal configurations. Every current or future private repository opts in through its own private PR, pinned to an approved hub commit.
7. **Central updates:** a repository-scoped GitHub App plus self-hosted Renovate can centrally open dependency and workflow update PRs for explicitly connected repositories. Patch/minor updates may merge only behind real required checks; major updates remain manual.

## Repository map (public only)

`policies/public-repositories.json` registers the **10 public repositories** found in this personal account on 2026-10-14, with stacks and the observed default branch. Private repositories are intentionally not named here, but can consume these public reusable workflows normally.

| Reusable workflow | Purpose | Call from consumer |
|---|---|---|
| `.github/workflows/node-ci.yml` | JS/TS/Next/React, npm/pnpm/yarn/bun | `.github/workflows/ci-shared.yml` |
| `.github/workflows/python-ci.yml` | Python lint, typing, test, build | `.github/workflows/ci-shared.yml` |
| `.github/workflows/dotnet-ci.yml` | C#/.NET restore, build, test | `.github/workflows/ci-shared.yml` |
| `.github/workflows/security-ci.yml` | secret scan + optional dependency audit | `.github/workflows/security-shared.yml` |
| `.github/workflows/guard.yml` | validate the hub itself | automatically on hub PRs |
| `.github/workflows/inventory.yml` | weekly read-only public policy status | schedule/manual |
| `.github/workflows/manager.yml` | central dependency/workflow update PRs | Monday convergence window/manual |

## High-assurance QA (including Arrival Confirmations coverage)

The hub has **14 opt-in reusable gates** and three hub-only workflows. In addition
to the language-specific core gates, it defines: advanced formatting/coverage/
bundle security, Playwright/accessibility/Lighthouse, fresh Supabase migrations/
integration/RLS, strict scheduled dependency audits, verified Vercel statuses
and Preview deployment registration, read-only Supabase Cloud app/API smoke,
production release verification, and
review-controlled Dependabot eligibility/auto-merge.

See [the precise Arrival Confirmations parity and limitations matrix](docs/ARRIVAL-PARITY.md)
and [an example central high-assurance caller](examples/arrival-grade-caller.yml.example).
**Do not claim the consumer is protected just because these YAML files exist.**
The caller must pin an actual published SHA, provide tests/credentials, run green,
and GitHub branch protection must explicitly require its checks.

## Adoption

1. Create **public** `Nisan-Sinai/github-workflows` (no organization) using [docs/SETUP.md](docs/SETUP.md).
2. Verify hub `guard.yml` passes, then record its actual immutable HEAD SHA.
3. Generate a caller and explicit manager opt-in with `python scripts/generate_consumer.py --repo Nisan-Sinai/artzi-energy --sha <40_HEX_SHA> --output ci-shared.yml --manager-output renovate.json` (local files only; it does **not** edit a repository). Change install and test commands to match the individual project's scripts.
4. Create a PR **in the consumer repo** with the generated `.github/workflows/ci-shared.yml`. Preserve its existing CI/branch protection/Vercel until all new jobs are proven green.
5. Only then, as a **separate approved change**, consider replacing duplicate jobs. Check the exact required status context names in GitHub; never remove old required checks before their replacements exist.
6. Repeat as needed. For a future repo, choose a profile from `policies/presets.json`; do not inherit the same test commands across unrelated stacks.

### Example (Node)

```yaml
name: Shared CI
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  node:
    uses: Nisan-Sinai/github-workflows/.github/workflows/node-ci.yml@0123456789abcdef0123456789abcdef01234567 # main; REPLACE the SHA with the actual approved commit
    with:
      package-manager: npm
      install-command: npm ci
      lint-command: npm run lint
      typecheck-command: npm run type-check
      test-command: npm run test:coverage
      build-command: npm run build
```

**This snippet is an example only.** Its SHA is a placeholder, not a published revision. Consumer workflows require a real published hub commit SHA, and the scripts must exist in that consumer.

## Rulesets and Dependabot

- `policies/rulesets/` contains **examples / templates only**. **A JSON file does not enforce branch protection** until a repository administrator imports it via GitHub Settings or an authorized API explicitly applies it.
- Reusable workflows cannot enforce the same rules on all personal repositories by themselves. Use read-only drift reporting, then approved settings changes.
- Dependabot configuration is repository-local (`.github/dependabot.yml`); the hub can supply a reference baseline but doesn't automatically take ownership of existing Dependabot settings.
- Existing auto-merge workflows should be kept until individually assessed; **Major** dependency updates need manual review.

## Documentation

- [First-time installation and Work handoff](docs/SETUP.md)
- [Security, permissions, limits](docs/SECURITY.md)
- [Adoption plan for today's repos](docs/ADOPTION.md)
- [Future repositories and upgrades](docs/FUTURE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Central repository manager and pilot](docs/CENTRAL-MANAGER.md)
- [Supabase Cloud safety and recovery](docs/SUPABASE-RECOVERY.md)

**Status:** published central workflow hub. A consumer is protected only after its own pinned caller PR is merged and its required checks are configured.
