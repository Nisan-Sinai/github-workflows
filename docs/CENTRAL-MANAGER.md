# Central repository manager

The hub can run one self-hosted Renovate instance and manage every repository
explicitly connected to it. The software and GitHub App are free. The public
hub's standard GitHub-hosted runner minutes are free as well.

## Security model

- Authentication uses a dedicated GitHub App, never a personal access token.
- The App is installed only on repositories selected by the owner. During the
  pilot it must be installed only on the temporary public test repository.
- The workflow mints a short-lived installation token. The private key remains
  in the `central-manager` environment's `MANAGER_PRIVATE_KEY` secret, the App
  client id in `MANAGER_CLIENT_ID`, and the comma-separated allowlist in
  `MANAGER_REPOSITORIES`.
- A repository is managed only when it contains `renovate.json` extending
  `github>Nisan-Sinai/github-workflows`. Installation alone is not opt-in.
- The central policy opens update PRs for application dependencies, lockfiles,
  GitHub Actions and SHA-pinned reusable workflows.
- Patch, minor, pin and digest updates may auto-merge only after GitHub reports
  the target repository's required checks successful. Major updates never
  auto-merge.
- Every connected default branch must have a fail-closed ruleset with real
  required check names before auto-merge is enabled.
- The connected repository must enable GitHub's auto-merge setting. Renovate
  requests squash auto-merge, while the ruleset remains the authority that
  blocks merging until every strict required check is green.

## Weekly convergence window

The manager runs six times on Monday at `03:00`, `03:30`, `04:00`, `04:30`,
`05:00` and `05:30` UTC. That is early Monday morning in Jerusalem and remains
inside Renovate's `before 9am on Monday` window across daylight-saving changes.
Repeated passes are intentional: after one strict PR merges, the remaining PRs
must be rebased and checked again. The five-PR concurrency ceiling plus six
passes lets the complete batch converge during the same maintenance window.

## One-time GitHub App setup

Create a private GitHub App owned by `Nisan-Sinai`, disable webhooks, and grant
only these repository permissions required by self-hosted Renovate:

- Checks: read/write
- Commit statuses: read/write
- Contents: read/write
- Dependabot alerts: read
- Issues: read/write
- Metadata: read
- Pull requests: read/write
- Workflows: read/write

Install it on the temporary pilot repository only. Generate one private key,
save it directly as the `MANAGER_PRIVATE_KEY` secret in the `central-manager`
environment, save the App client id as `MANAGER_CLIENT_ID`, and set
`MANAGER_REPOSITORIES` to the exact pilot repository name. Then delete the
downloaded key file. Never paste the key in an issue, PR, chat, source file or
log. The workflow also passes the allowlist to token minting, so even an App
installed on more repositories cannot grant this job blanket access.

For each connected repository, enable **Allow auto-merge** and automatic branch
deletion in repository settings. These settings do not weaken branch rules:
GitHub still refuses the merge until all required checks and the strict
up-to-date requirement pass.

## Connect a repository

After its CI and branch rules are verified, add this file by reviewed PR:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["github>Nisan-Sinai/github-workflows"]
}
```

The App installation defines the maximum access boundary; `renovate.json`
defines the repositories that have opted in. Future repositories are not
modified merely because they exist.

## Private repositories

The pilot uses a public test repository, so its name and Renovate logs are not
sensitive. Before installing the App on a private repository, move the manager
runner to a private administration repository or add verified log redaction;
otherwise a public Actions log could reveal private repository metadata. The
shared policy can remain in this public hub.
