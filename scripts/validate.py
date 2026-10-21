#!/usr/bin/env python3
"""Offline, read-only validation of the reusable-workflow hub.

The hub must remain safe to extend: new repositories in the public catalog
must not require editing a fixed count or replacing existing project CI.
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github/workflows'
REUSABLE = {
    'node-ci.yml', 'python-ci.yml', 'dotnet-ci.yml',
    'security-ci.yml', 'vercel-gate.yml', 'vercel-preview-deployment.yml',
    'dependabot-eligibility.yml', 'dependabot-automerge.yml',
    'advanced-node-qa.yml', 'browser-qa.yml', 'supabase-qa.yml',
    'supabase-cloud-qa.yml', 'postgres-contract.yml', 'production-qa.yml', 'dependency-watch.yml',
    'deployment-smoke.yml',
}
RUNNERS = {'guard.yml', 'inventory.yml', 'manager.yml'}
ALLOWED_EVENTS = {'workflow_call', 'pull_request', 'push', 'schedule', 'workflow_dispatch'}


def parse_yaml(path):
    # BaseLoader correctly preserves GitHub Actions' `on` rather than YAML 1.1 Boolean True.
    data = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    if not isinstance(data, dict):
        raise ValueError(f'{path}: expected mapping')
    return data


def check(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    index = json.loads((ROOT / 'policies/public-repositories.json').read_text(encoding='utf-8'))
    presets = json.loads((ROOT / 'policies/presets.json').read_text(encoding='utf-8'))
    manager = json.loads((ROOT / 'renovate/global.json').read_text(encoding='utf-8'))
    central_policy = json.loads((ROOT / 'default.json').read_text(encoding='utf-8'))
    check(index.get('owner') == 'Nisan-Sinai', 'Public catalog must only target the personal account')
    repos = index.get('repositories')
    check(isinstance(repos, list) and repos, 'Public catalog must be nonempty')
    check(len({r['name'] for r in repos}) == len(repos), 'Duplicate repositories in catalog')
    for row in repos:
        check(bool(re.fullmatch(r'[A-Za-z0-9_.-]+', row['name'])), 'Invalid repository name')
        check(bool(re.fullmatch(r'[A-Za-z0-9._/-]+', row['branch'])), 'Invalid branch')
        check(row['profile'] in presets, f'Unknown stack profile for {row["name"]}')
        check(row['adoption'] in {'assess', 'preserve-existing-ci', 'opt-in'}, 'Invalid adoption strategy')
        check(not any(k in row for k in ('private', 'secrets', 'token')), 'Private data in public catalog')

    check(manager.get('platform') == 'github', 'Manager must target GitHub')
    check(manager.get('autodiscover') is True, 'Manager must discover App-installed repositories')
    check(manager.get('onboarding') is False, 'Manager must never silently onboard repositories')
    check(manager.get('requireConfig') == 'required', 'Every managed repository must explicitly opt in')
    check('repositories' not in manager, 'Public manager config must not contain repository inventory')
    check(central_policy.get('platformAutomerge') is False,
          'Renovate must evaluate checks itself before automerge')
    check(central_policy.get('ignoreTests') is False,
          'Renovate must never ignore repository checks')
    check(central_policy.get('automergeStrategy') == 'squash',
          'Automatic dependency updates must use squash merges')
    rules = central_policy.get('packageRules')
    check(isinstance(rules, list) and rules, 'Central update policy needs package rules')
    major = [r for r in rules if 'major' in r.get('matchUpdateTypes', [])]
    check(major and all(r.get('automerge') is False for r in major), 'Major updates must never auto-merge')
    automatic = [r for r in rules if r.get('automerge') is True]
    check(automatic and all('major' not in r.get('matchUpdateTypes', []) for r in automatic),
          'Automatic updates must exclude major versions')
    check(all(r.get('platformAutomerge') is False for r in automatic),
          'Automatic updates must not use unsafe platform automerge')
    check(all(r.get('ignoreTests') is False for r in automatic),
          'Automatic updates must wait for repository checks')

    paths = list(WORKFLOWS.glob('*.yml'))
    discovered = {p.name for p in paths}
    check(discovered == REUSABLE | RUNNERS,
          f'Unexpected/missing workflow files: {sorted(discovered ^ (REUSABLE | RUNNERS))}')
    for path in paths:
        data = parse_yaml(path)
        check(isinstance(data.get('jobs'), dict) and data['jobs'], f'{path}: missing jobs')
        triggers = data.get('on')
        check(isinstance(triggers, dict) and triggers, f'{path}: invalid events')
        check(set(triggers) <= ALLOWED_EVENTS, f'{path}: unexpected trigger')
        check(isinstance(data.get('permissions'), dict), f'{path}: missing permissions')
        check(data['permissions'].get('contents') in {'read', 'write'}, f'{path}: bad contents permissions')
        if path.name in REUSABLE:
            check('workflow_call' in triggers and len(triggers) == 1,
                  f'{path}: shared workflows must be called explicitly, not run automatically')
        else:
            check('workflow_call' not in triggers, f'{path}: hub-only workflow must not be callable')

        for jobname, job in data['jobs'].items():
            if 'uses' in job:
                # GitHub Actions does not allow timeout-minutes on reusable
                # workflow invocation jobs. The called workflow owns the limit.
                check(job['uses'] in {'./.github/workflows/' + name for name in REUSABLE},
                      f'{path}:{jobname}: unapproved local workflow invocation')
                check('steps' not in job and 'timeout-minutes' not in job,
                      f'{path}:{jobname}: invalid caller job configuration')
            else:
                check('timeout-minutes' in job, f'{path}:{jobname}: unbounded job timeout')
            if 'steps' in job:
                for step in job['steps']:
                    ref = step.get('uses', '')
                    if ref.startswith('actions/checkout@'):
                        check(step.get('with', {}).get('persist-credentials') == 'false',
                              f'{path}: checkout must disable credential persistence')
                    # Public shared workflows are infrastructure; unpinned
                    # third-party actions are a mutable remote execution channel.
                    if ref and not ref.startswith('./'):
                        check(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@'+r'[0-9a-f]{40}', ref)),
                              f'{path}: action must use an immutable 40-character commit SHA: {ref}')
                    check(step.get('continue-on-error') != 'true',
                          f'{path}: silent failure suppression is forbidden')
        if path.name == 'security-ci.yml':
            secret_steps = data['jobs']['secrets']['steps']
            check(any(s.get('uses', '').startswith('actions/checkout@')
                      and s.get('with', {}).get('fetch-depth') == '0'
                      for s in secret_steps),
                  'Secret scan must fetch the complete Git history')
            check(any(s.get('run') == 'gitleaks git --redact --verbose .'
                      for s in secret_steps),
                  'Secret scan must scan the complete Git history with redaction')
        if path.name == 'dependabot-automerge.yml':
            gate_permissions = data['jobs']['gate'].get('permissions', {})
            check(gate_permissions.get('contents') == 'write', 'Auto-merge needs scoped write')
            check(gate_permissions.get('pull-requests') == 'write', 'Auto-merge needs PR write')
            check(triggers['workflow_call']['inputs']['enable-merge']['default'] == 'false',
                  'Auto-merge must default to a dry run')
        elif path.name == 'vercel-preview-deployment.yml':
            preview_permissions = data['jobs']['verify-preview'].get('permissions', {})
            check(preview_permissions.get('deployments') == 'write',
                  'Preview registration needs deploy write')
            check(preview_permissions.get('contents') == 'read',
                  'Preview registration needs read-only code')
        else:
            check(data['permissions'].get('contents') == 'read', f'{path}: unnecessary code write permission')
            check(data['permissions'].get('pull-requests') != 'write', f'{path}: unnecessary PR writes')

    print(f'Validated {len(paths)} workflows, {len(repos)} public records, '
          f'{len(REUSABLE)} opt-in reusable gates')


if __name__ == '__main__':
    validate()
