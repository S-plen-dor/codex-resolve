"""Project-local history, atomic state updates and a generated handoff companion."""
import json
import os
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from .project import inspect, write_new


def atomic_json(path, data):
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    write_new(temp, data)
    os.replace(temp, path)


def root_path(value):
    root = Path(value).expanduser().resolve(strict=True)
    inspect(root)
    return root


def reference(root, value):
    if value is None:
        return None
    path = Path(value).expanduser().resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def handoff(root, state):
    lines = ['# Generated project handoff', '',
             'Generated from state.json. Keep narrative notes in HANDOFF.md and creative-brief.md.', '',
             '```json', json.dumps(state, ensure_ascii=False, indent=2), '```', '',
             'Inspect linked artifacts before acting. Recorded completion is not perceptual approval.', '']
    temp = root/('HANDOFF.auto.'+uuid.uuid4().hex+'.tmp')
    temp.write_text('\n'.join(lines), encoding='utf-8')
    os.replace(temp, root/'HANDOFF.auto.md')


def reset_preview(state):
    for key in ('current_collection', 'current_preview', 'current_review'):
        state[key] = None
    for key in ('review_declaration', 'review_timeline_range', 'current_preview_range', 'technical_qc'):
        state.pop(key, None)


def update(root, command, args, result, error=None):
    if command == 'produce' and not error:
        from types import SimpleNamespace
        if result.get('revision_result'):
            update(root, 'plan-revise', SimpleNamespace(), result['revision_result'])
        update(root, 'plan-apply', SimpleNamespace(plan=result['plan']), result['build'])
        update(root, 'render-submit', SimpleNamespace(), result['render'])
    state = inspect(root)['state.json']
    stamp = datetime.now(timezone.utc).isoformat()
    event_id = uuid.uuid4().hex
    event = {'schema_version': 1, 'id': event_id, 'created_utc': stamp,
             'command': command, 'status': 'failed' if error else 'completed',
             'result': result, 'error': error}
    state['last_event'] = event_id
    state['updated_utc'] = stamp
    if error:
        state['last_error'] = {'command': command, 'message': error}
        state['next_action'] = 'Inspect failed operation records before retrying'
        if command == 'plan-apply':
            state['failed_operation'] = reference(root, Path(args.out)/'operation.json')
        elif command == 'render-submit':
            state['failed_render'] = reference(root, Path(args.out)/'render.json')
        elif command == 'produce':
            state['failed_workflow'] = reference(root, Path(args.out)/'workflow.json')
        elif command == 'render-collect':
            state['failed_collection'] = reference(root, Path(args.out)/'collection.json')
    else:
        state['last_error'] = None
        if command == 'observe':
            state['latest_observation'] = reference(root, result['observation'])
            packs = state.setdefault('observations', [])
            if state['latest_observation'] not in packs:
                packs.append(state['latest_observation'])
            state['next_action'] = 'Open actual observation images/clip and decide whether to refine the plan'
        elif command in ('plan-register', 'plan-revise'):
            changed = state.get('plan_sha256') != result['plan_sha256']
            state['current_plan'] = reference(root, result['plan'])
            state['plan_sha256'] = result['plan_sha256']
            state['plan_revision'] = result['revision']
            if changed:
                state['stage'] = 'planned'
                for field in ('operation', 'render', 'timeline'):
                    if state.get('current_'+field):
                        state['previous_'+field] = state['current_'+field]
                state['current_operation'] = None
                state['current_render'] = None
                state['current_timeline'] = None
                state['current_timeline_id'] = None
                state['current_preview_matches_plan'] = False
                reset_preview(state)
                state['plan_needs_build'] = True
                state['next_action'] = 'Inspect plan changes, then build a new work timeline when authorized'
            if command == 'plan-revise':
                state['latest_feedback'] = result['feedback']
                state['latest_revision_record'] = reference(root, result['plan']+'.revision.json')
        elif command == 'plan-apply':
            for field in ('operation', 'render'):
                if state.get('current_'+field):
                    state['previous_'+field] = state['current_'+field]
            state['current_render'] = None
            state['latest_render_matches_plan'] = False
            reset_preview(state)
            state.update(current_plan=reference(root, args.plan), plan_sha256=result['plan_sha256'],
                         plan_revision=result['revision'],
                         current_operation=reference(root, result['operation']),
                         current_timeline=result['timeline'], current_project=result['project'],
                         current_timeline_id=result['timeline_id'], stage='built_not_reviewed',
                         plan_needs_build=False, current_preview_matches_plan=False)
            state['next_action'] = 'Submit a preview using the current operation and a chosen render preset'
        elif command == 'render-submit':
            state['latest_render'] = reference(root, result['record'])
            matches = (state.get('current_operation') == reference(root, result['operation'])
                       and not state.get('plan_needs_build', True))
            state['latest_render_matches_plan'] = matches
            if matches:
                state['current_render'] = reference(root, result['record'])
                state['stage'] = result['status']
                state['current_preview_matches_plan'] = False
                reset_preview(state)
                state['next_action'] = 'Query the recorded job; then locate and inspect actual output'
        elif command == 'render-status':
            state['last_render_status'] = result
            if reference(root, args.record) == state.get('current_render'):
                raw = result['status']
                job_status = raw.get('JobStatus', '') if isinstance(raw, dict) else str(raw)
                state['render_job_status'] = job_status
                normalized = job_status.casefold()
                if normalized in ('complete', 'completed'):
                    state['stage'] = 'render_complete_not_reviewed'
                elif normalized in ('failed', 'cancelled', 'canceled'):
                    state['stage'] = 'render_failed_or_cancelled'
                elif normalized in ('rendering', 'in progress'):
                    state['stage'] = 'rendering'
                state['next_action'] = 'Inspect reported task state; a completed job still needs actual output review'
        elif command == 'produce':
            state['current_workflow'] = reference(root, result['workflow'])
        elif command == 'render-collect':
            state['latest_collection'] = reference(root, result['collection'])
            if (reference(root, result['render_record']) == state.get('current_render')
                    and result['plan_sha256'] == state.get('plan_sha256')):
                reset_preview(state)
                state['current_collection'] = state['latest_collection']
                state['current_preview'] = reference(root, result['media'])
                state['current_preview_range'] = result['timeline_range']
                state['current_preview_matches_plan'] = True
                state['current_review'] = None
                state['stage'] = 'collected_not_reviewed'
                state['technical_qc'] = result['qc']
                if isinstance(result['qc'], dict) and result['qc'].get('passed') is False:
                    state['stage'] = 'technical_qc_failed'
                state['next_action'] = 'Open actual preview and record review scope or explicit skipped status'
        elif command == 'review-record':
            state['latest_review'] = reference(root, result['review_record'])
            if (reference(root, result['render_record']) == state.get('current_render')
                    and result['plan_sha256'] == state.get('plan_sha256')):
                state['current_review'] = state['latest_review']
                state['review_declaration'] = result['declaration']
                state['review_timeline_range'] = result['timeline_range']
                state['stage'] = 'review_declared_'+result['declaration']['status']
                state['next_action'] = ('Interpret feedback and revise a new plan' if
                    result['declaration']['status'] == 'changes_requested' else
                    'Deliver or continue according to the declared review scope and current user request')
    history = root/'history'
    history.mkdir(exist_ok=True)
    # Durable event includes resulting state so interrupted state/handoff writes can be reconstructed.
    event['state_after'] = state
    write_new(history/(stamp.replace(':', '-')+'-'+event_id+'.json'), event)
    atomic_json(root/'state.json', state)
    handoff(root, state)


def run(args, callback):
    workspace = getattr(args, 'workspace', None)
    if not workspace:
        return callback()
    root = root_path(workspace)
    lock = root/'.codex-resolve.lock'
    # Held across the command so two cooperating CLI sessions cannot advance one project concurrently.
    try:
        stream = lock.open('x', encoding='utf-8')
    except FileExistsError as exc:
        raise ValueError('Workspace is locked; inspect the owning process before removing a stale lock') from exc
    with stream:
        stream.write(json.dumps({'pid': os.getpid(), 'command': args.command}))
        stream.flush()
        try:
            try:
                result = callback()
            except Exception as exc:
                try:
                    update(root, args.command, args, None, str(exc))
                except Exception as state_error:
                    raise RuntimeError(f'{exc}; additionally failed to record state: {state_error}') from exc
                raise
            try:
                update(root, args.command, args, result)
            except Exception as exc:
                raise RuntimeError('Command completed but project tracking failed. Do not rerun mutations blindly. '
                                   f'Result: {json.dumps(result, ensure_ascii=False)}; state error: {exc}') from exc
            return {**result, 'workspace_state': str(root/'state.json')}
        finally:
            stream.close()
            lock.unlink()


def resume(directory):
    root = root_path(directory)
    state = inspect(root)['state.json']
    missing = []
    for field in ('current_plan', 'current_operation', 'current_render', 'latest_observation',
                  'current_collection', 'current_preview', 'current_review', 'current_workflow'):
        value = state.get(field)
        if value and not (root/value).is_file():
            missing.append({'field': field, 'path': value})
    changed = None
    if state.get('current_plan') and state.get('plan_sha256'):
        selected = root/state['current_plan']
        if selected.is_file():
            changed = hashlib.sha256(selected.read_bytes()).hexdigest() != state['plan_sha256']
    return {'project': inspect(root)['project.json'], 'state': state, 'missing_artifacts': missing,
            'current_plan_changed_on_disk': changed,
            'locked': (root/'.codex-resolve.lock').exists(),
            'read_next': ['HANDOFF.auto.md', 'HANDOFF.md', 'creative-brief.md'],
            'scope': 'Read-only project context, not a live Resolve query or automatic recovery'}
