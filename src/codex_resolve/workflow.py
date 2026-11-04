"""One invocation builds a new version and queues its preview; never invents creative decisions."""
from pathlib import Path

from .execution import apply, render, save_record
from .plan import executable, load_plan
from .revision import revise


def produce(plan, output, project, timeline, preset, save_current=False, start=False,
            changes=None, revision=None, start_frame=0, end_frame=None, width=None, height=None):
    executable(load_plan(plan))
    if changes and not revision:
        raise ValueError('Feedback production requires a new --revision')
    root = Path(output).expanduser().resolve()
    if root.exists():
        raise ValueError('Workflow directory must be new; inspect old workflow records before retrying')
    root.mkdir(parents=True)
    journal = root/'workflow.json'
    record = {'kind': 'produce', 'status': 'preparing', 'plan': str(Path(plan).resolve())}
    save_record(journal, record)
    try:
        if changes:
            record['revision_result'] = revise(plan, changes, root/'revised-plan.json', revision)
            record['plan'] = record['revision_result']['plan']
            record['status'] = 'revised'
            save_record(journal, record)
        record['build'] = apply(record['plan'], project, timeline, root/'build', save_current)
        record['status'] = 'built'
        save_record(journal, record)
        record['render'] = render(record['build']['operation'], root/'preview', preset, start,
                                  start_frame, end_frame, width, height)
        record['status'] = record['render']['status']
    except Exception as exc:
        record.update(status='failed_partial', error=str(exc))
        raise
    finally:
        save_record(journal, record)
    return {'workflow': str(journal), **record}
