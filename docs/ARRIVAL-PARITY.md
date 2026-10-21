# Arrival Confirmations high-assurance QA — coverage and boundaries

This document compares the **source workflow definitions** in
`Nisan-Sinai/arrival-confirmations` with the **reusable primitives** maintained
here. It is a coverage map, **not** proof that any consumer has adopted these
primitives. Adoption is via a reviewed caller workflow pinned to the hub's
full SHA, and the consumer's existing checks must not be removed prematurely.

| Arrival Confirmations functionality | Shared definition maintained here | Consumer responsibility |
|---|---|---|
| Prettier/ESLint/TypeScript/build | `node-ci.yml`, `advanced-node-qa.yml` | Supply existing scripts and lockfile install |
| Unit/component coverage and budgets | `advanced-node-qa.yml` | Keep actual tests and coverage thresholds in project |
| Browser bundle/security tests | `advanced-node-qa.yml` | Supply `test:security` or equivalent |
| Deadcode and built-artifact secrets scan | `advanced-node-qa.yml` | Supply real project scripts |
| Full-history secret scan | `security-ci.yml` | Maintain scanner availability/licensing for target visibility |
| Production AND full dependency audit | `security-ci.yml`, `dependency-watch.yml` | Supply strict all-dependencies audit, schedule in caller |
| Migrations/schema drift | `supabase-qa.yml` | Actual Supabase migrations, schema comparison tests |
| Integration, RLS, 50-event isolation | `supabase-qa.yml` | Real integration/SQL tests, pass `event-matrix-command` for RSVP-grade parity |
| Active Supabase Cloud app/API | `supabase-cloud-qa.yml` | Pass only the exact project URL and publishable/anon key; keep management and service-role credentials out of this gate |
| Playwright browser E2E and axe accessibility | `browser-qa.yml` | Actual specs and appropriate credentials; no fake passing tests |
| Lighthouse budgets and artifacts | `browser-qa.yml` | Real Lighthouse command, serve the app, enforce budgets |
| Genuine Vercel commit status | `vercel-gate.yml` | Set exact context/project; configure Vercel |
| Register an actual verified Preview deployment | `vercel-preview-deployment.yml` | Opt in, grant `deployments: write`, specify project |
| Production content and exact deployed commit | `production-qa.yml` | Implement a verifier that **really checks** production SHA; schedule/push in caller |
| Isolated HTTP load and measured budgets | `isolated-load-qa.yml` | Keep app-specific safety/load scripts; localhost only, no production-capacity claim |
| Patch/Minor Dependabot gate | `dependabot-eligibility.yml`, `dependabot-automerge.yml` | Explicit adoption and exact check names; merge off by default |
| Regular vulnerability monitoring | `dependency-watch.yml` | Schedule in caller, strict install and audit command |
| WhatsApp reminders and live business features | **Not generalized** | Keep in the application (currently disabled in RSVP) |
| Branch protection and required review/checks | `policies/rulesets`, `render_ruleset.py`, `admin_ruleset.py` | Requires real GitHub admin import/approval; files alone do not enforce rules |

## What “full coverage” means

The hub owns **workflow orchestration, gate design and policy schemas**, but
cannot own or execute another repository's proprietary app tests without a
caller and the app's code/configuration. For example, a central RLS job runs
`pnpm test:rls` *in the consumer checkout*; RLS policies and assertions remain
in the consumer. A central E2E runner does **not** secretly carry production
credentials or replace production-integration tests with placeholders.

- Project-specific secrets are never committed to this public repo. Declare
  and pass them in the consuming repository's secure workflow, following that
  project's Dependabot vs human-PR credentials policy.
- Schedule frequency (6-hour strict dependency watch, daily production smoke)
  is configured in the **consumer**. A schedule in the hub only runs against
  the hub itself, never against a consumer.
- The generic production verifier checks required inputs and executes a
  consumer-provided verifier; it does not currently write the special
  `Production integrity` commit status used by RSVP.
- The verified Preview workflow **does** create a GitHub Deployment record,
  but only after the exact PR HEAD's authentic Vercel status is green.
- The 50-event test matrix is **not embedded in the hub**; the test suite remains
  in RSVP, and its command can be a mandatory consumer gate.
- Calling the shared workflows with explicit full-SHA pins is safer than
  making every consumer import `@main` automatically.

## Migration acceptance criteria

1. Keep all five existing RSVP CI jobs and Vercel checks required until the
   corresponding shared jobs are truly green on PRs (including Dependabot).
2. Verify Supabase local migrations and RLS tests run against a fresh DB.
3. Verify real Playwright/axe coverage and Lighthouse budgets; don't count
   skipped live-invitation scenarios as tested.
4. Confirm the genuine GitHub Deployment Preview and deployed production SHA.
5. Migrate branch required-check names only after checking their exact new
   status names and preserving protection. Never bypass protection to migrate.
6. Do not switch Dependabot automatic merging on without explicit approval.

The hub is therefore **capable of hosting** RSVP-grade gates; it does not
pretend those gates have been enabled on other repositories.
