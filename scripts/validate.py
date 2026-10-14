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
    'production-qa.yml', 'dependency-watch.yml',
}
RUNNERS = {'guard.yml', 'inventory.yml'}
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
            check('timeout-minutes' in job, f'{path}:{jobname}: unbounded job timeout')
            if 'steps' in job:
                for step in job['steps']:
                    ref = step.get('uses', '')
                    if ref.startswith('actions/checkout@'):
                        check(step.get('with', {}).get('persist-credentials') == 'false',
                              f'{path}: checkout must disable credential persistence')
                    check(not (ref.endswith('@main') or ref.endswith('@master')),
                          f'{path}: floating third-party action ref')
        if path.name == 'dependabot-automerge.yml':
            check(data['permissions'].get('contents') == 'write', 'Auto-merge needs scoped write')
            check(data['permissions'].get('pull-requests') == 'write', 'Auto-merge needs PR write')
            check(triggers['workflow_call']['inputs']['enable-merge']['default'] == 'false',
                  'Auto-merge must default to a dry run')
        elif path.name == 'vercel-preview-deployment.yml':
            check(data['permissions'].get('deployments') == 'write', 'Preview registration needs deploy write')
            check(data['permissions'].get('contents') == 'read', 'Preview registration needs read-only code')
        else:
            check(data['permissions'].get('contents') == 'read', f'{path}: unnecessary code write permission')
            check(data['permissions'].get('pull-requests') != 'write', f'{path}: unnecessary PR writes')

    print(f'Validated {len(paths)} workflows, {len(repos)} public records, '
          f'{len(REUSABLE)} opt-in reusable gates')


if __name__ == '__main__':
    validate()
