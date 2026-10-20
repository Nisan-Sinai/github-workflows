# Central repository manager

The hub runs one self-hosted Renovate instance for repositories explicitly
connected through the `Nisan-Sinai Central Manager` GitHub App. Renovate, the
GitHub App and public-repository GitHub-hosted Actions usage are free.

## Three-layer opt-in boundary

A repository is managed only when all three conditions are true:

1. The owner selects it in the GitHub App installation.
2. The manager workflow includes it in the token's exact repository allowlist.
3. Its default branch contains `renovate.json` extending
   `github>Nisan-Sinai/github-workflows`.

The App installation is the outer access boundary. The short-lived token is
narrower: the two current public repositories are listed explicitly in the
workflow, while future private repository names belong in the protected
`MANAGER_PRIVATE_REPOSITORIES` environment secret. Public names may be added
by reviewed hub PR. A future repository is never modified merely because it
exists or because the App is installed on it.

Before Renovate starts, the workflow enumerates only the repositories visible
to that scoped token and masks both their full and short names in Actions logs.
This keeps future private repository names out of the public log.

## Security model

- Authentication uses a dedicated GitHub App, never a personal access token.
- Long-lived values are stored only in the protected `central-manager`
  environment: `MANAGER_CLIENT_ID`, `MANAGER_PRIVATE_KEY`, and the optional
  `MANAGER_PRIVATE_REPOSITORIES` name allowlist.
- Installation tokens are minted for one job and revoked in the action's post
  step.
- Checkout credential persistence is disabled.
- Actions and the Renovate container are pinned to immutable digests.
- Patch, minor, pin and digest updates may auto-merge. Renovate itself performs
  the merge only after every observed status check succeeds
  (`platformAutomerge: false`, `ignoreTests: false`).
- Major updates require Dependency Dashboard approval and manual review.
- Repository branch rules remain recommended as defense in depth for human
  changes and direct pushes.

## Schedule and policy-change verification

The regular manager window runs six times on Monday at `03:00`, `03:30`,
`04:00`, `04:30`, `05:00` and `05:30` UTC. Repeated passes let Renovate
merge one green update, rebase the rest and evaluate the next update during the
same maintenance window.

A push to `main` that changes `default.json`, `renovate/global.json` or
the manager workflow triggers one immediate verification run and bypasses only
Renovate's branch-creation schedule. It does not bypass release age, CI,
major-update review or repository access controls.

Manual dispatches honor the Monday schedule unless
`ignore_schedule: true` is deliberately selected.

## GitHub App setup

Create a private GitHub App owned by `Nisan-Sinai`, disable webhooks, and
grant only these repository permissions required by self-hosted Renovate:

- Checks: read/write
- Commit statuses: read/write
- Contents: read/write
- Dependabot alerts: read
- Issues: read/write
- Metadata: read
- Pull requests: read/write
- Workflows: read/write

Install it with **Only select repositories**. Generate one private key, save it
directly as `MANAGER_PRIVATE_KEY` in the `central-manager` environment, save
the client id as `MANAGER_CLIENT_ID`, then delete the downloaded key file.
Never paste the key in source, an issue, PR, chat or log.

The legacy `MANAGER_REPOSITORIES` secret is unused and should be deleted. For
future private repositories, create or update `MANAGER_PRIVATE_REPOSITORIES`
with names separated by commas or new lines.

## Connect a repository

After its CI is verified:

1. Select the repository in the App installation.
2. Add its name to the exact public or private manager allowlist.
3. Merge this opt-in file by reviewed PR:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>Nisan-Sinai/github-workflows"]
}
```

Removing any one of the three layers disconnects the repository.

## Recovery

To stop all centralized dependency writes immediately, revoke/delete
`MANAGER_PRIVATE_KEY`. To disconnect one repository, remove it from the App
installation and the token allowlist, then delete its `renovate.json` in a
reviewed PR. Disconnecting the manager does not change application code or
Supabase data.
