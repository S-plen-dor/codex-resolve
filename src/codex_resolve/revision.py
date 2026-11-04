"""Agent-authored clip changes; no natural-language parser or Resolve mutations."""
import copy
import json
import os
from pathlib import Path

from .plan import bounds, load_plan
from .project import write_new


def locate(path, start, end=None):
    plan = load_plan(path)
    start, end = bounds([start, start+1 if end is None else end], 'lookup range')
    matches = []
    for group in ('shots', 'audio'):
        for row in plan['data'].get(group, []):
            a, b = row['timeline_range']
            if a < end and b > start:
                matches.append({'group': group, **row})
    return {'plan_sha256': plan['sha256'], 'revision': plan['data']['revision'],
            'timeline_range': [start, end], 'clips': matches,
            'scope': 'Timeline-frame lookup only; semantic intent is interpreted by Codex'}


def revise(path, changes, output, revision):
    base = load_plan(path)
    patch_path = Path(changes).expanduser().resolve(strict=True)
    patch = json.loads(patch_path.read_text(encoding='utf-8'))
    if patch.get('schema_version') != 1 or patch.get('base_sha256') != base['sha256']:
        raise ValueError('Changes must identify the exact base plan SHA-256')
    if not isinstance(patch.get('feedback'), str) or not patch['feedback'].strip():
        raise ValueError('Record the original user feedback in changes.feedback')
    if not isinstance(revision, str) or not revision.strip() or revision == base['data']['revision']:
        raise ValueError('Provide a new nonempty revision')
    operations = patch.get('operations')
    if not isinstance(operations, list) or not operations:
        raise ValueError('Provide nonempty clip operations')
    target = Path(output).expanduser().resolve()
    if target.exists() or Path(str(target)+'.revision.json').exists():
        raise ValueError('Plan and revision record paths must be new')
    data = copy.deepcopy(base['data'])
    changed = set()
    for op in operations:
        group, key, action = op['group'], op['id'], op['action']
        if group not in ('shots', 'audio') or not isinstance(key, str) or not key:
            raise ValueError('Each operation needs a shots/audio group and stable ID')
        if key in changed:
            raise ValueError('Combine changes to the same clip into one operation')
        changed.add(key)
        rows = data.setdefault(group, [])
        index = next((i for i, row in enumerate(rows) if row['id'] == key), None)
        if action == 'add':
            if index is not None or op['clip'].get('id') != key:
                raise ValueError('Added clip requires a new matching ID')
            rows.append(copy.deepcopy(op['clip']))
        elif action == 'remove':
            if index is None:
                raise ValueError('Unknown clip: '+key)
            rows.pop(index)
        elif action == 'update':
            if index is None:
                raise ValueError('Unknown clip: '+key)
            values, unset = op.get('set', {}), op.get('unset', [])
            if not isinstance(values, dict) or not isinstance(unset, list):
                raise ValueError('update requires set object and optional unset list')
            if not values and not unset:
                raise ValueError('update must set or unset at least one field')
            if 'id' in values or set(unset) & {'id', 'source_id', 'source_range', 'timeline_range'}:
                raise ValueError('Stable IDs cannot be changed; required clip fields cannot be removed')
            if set(values) & set(unset):
                raise ValueError('Cannot set and unset the same field')
            rows[index].update(copy.deepcopy(values))
            for field in unset:
                if not isinstance(field, str):
                    raise ValueError('unset entries must be field names')
                rows[index].pop(field, None)
        else:
            raise ValueError('Unsupported action: '+str(action))
    # Accepted clips can be protected explicitly. Everything untouched stays byte-equivalent as data.
    protected = patch.get('preserve_ids', [])
    if not isinstance(protected, list) or any(not isinstance(k, str) for k in protected):
        raise ValueError('preserve_ids must be a list of clip IDs')
    before = {r['id']: r for g in ('shots', 'audio') for r in base['data'].get(g, [])}
    after = {r['id']: r for g in ('shots', 'audio') for r in data.get(g, [])}
    for key in protected:
        if key not in before or after.get(key) != before[key]:
            raise ValueError('Protected clip changed or missing: '+key)
    data['revision'] = revision
    # Preserve path meaning if the new revision is in a different directory.
    data['project_root'] = os.path.relpath(base['root'], target.parent)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Validate a sibling draft before publishing the new plan. Leave it on failure as evidence.
    draft = target.with_name(target.name+'.draft')
    write_new(draft, data)
    validated = load_plan(draft)
    # Exclusive publication prevents overwriting a concurrently created revision.
    with target.open('xb') as stream:
        stream.write(draft.read_bytes())
    draft.unlink()
    record = {'schema_version': 1, 'base_plan': base['path'], 'base_sha256': base['sha256'],
              'plan': str(target), 'plan_sha256': validated['sha256'], 'revision': revision,
              'feedback': patch['feedback'], 'interpretation': patch.get('interpretation'),
              'changes_file': str(patch_path), 'operations': operations, 'preserve_ids': protected,
              'scope': 'New plan only; no implicit ripple, Resolve execution or preview generation'}
    write_new(Path(str(target)+'.revision.json'), record)
    return record
