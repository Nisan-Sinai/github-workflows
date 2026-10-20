# Central repository manager

The hub runs one self-hosted Renovate instance for repositories explicitly
connected through the `Nisan-Sinai Central Manager` GitHub App. Renovate, the
GitHub App and public-repository GitHub-hosted Actions usage are free.

## Two-layer opt-in boundary

A repository is managed only when both conditions are true:

1. The owner selects it in the GitHub App installation.
2. Its default branch contains `renovate.json` extending
   `github>Nisan-Sinai/github-workflows`.

The App installation is the maximum access boundary. The workflow passes only
`owner` to `actions/create-github-app-token`; GitHub then scopes the
short-lived token to every repository selected in that installation. No
repository inventory is stored in source or in an allowlist secret. Adding a
future repository means selecting it in the App installation and merging the
small opt-in file after its CI is ready.

Before Renovate starts, the workflow enumerates the installation with the
short-lived token and masks both full and short repository names in Actions
logs. This prevents a public manager log from revealing a future private
repository name.

## Security model

- Authentication uses a dedicated GitHub App, never a personal access token.
- The only long-lived manager secrets are `MANAGER_CLIENT_ID` and
  `MANAGER_PRIVATE_KEY` in the protected `central-manager` environment.
- Installation tokens are minted for one job and revoked in the action's post
  step.
- Checkout credential persistence is disabled.
- Actions and the Renovate container are pinned to immutable digests.
- The central policy updates application dependencies, lockfiles, GitHub
  Actions and SHA-pinned reusable workflows.
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
major-update review or the App installation boundary.

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

The old `MANAGER_REPOSITORIES` secret is not used and should be deleted.

## Connect a repository

After its CI is verified, add this file by reviewed PR:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>Nisan-Sinai/github-workflows"]
}
```

Then select the repository in the App installation. Removing either the App
selection or `renovate.json` disconnects it.

## Recovery

To stop all centralized dependency writes immediately, remove repositories from
the App installation or revoke/delete `MANAGER_PRIVATE_KEY`. To disconnect a
single repository, remove it from the App installation and delete its
`renovate.json` in a reviewed PR. Existing application code and Supabase data
are not changed by disconnecting the manager.
