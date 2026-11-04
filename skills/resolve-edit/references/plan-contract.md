# Plan and production contract

This contract applies only when choosing this package's plan-based executor. Direct API calls, other tools and project-specific scripts do not need to follow this file format or command sequence. When used, Codex can maintain the files for the user. All shipped adapters are unverified development code; examples are optional.

## Plan

schema_version=1, nonempty revision, project_root resolved from plan file directory, timeline={fps rational string,width,height}. sources have unique id, path relative to project_root, optional sha256. Video requires fps matching the timeline; audio-only sources use kind=audio and may omit fps (timeline-rate frame coordinates). No VFR/mixed-rate video adapter yet.

shots is a nonempty array; audio is an independent array, possibly empty. Each clip: unique id across both groups, source_id, source_range=[start,end), timeline_range=[start,end), optional track (one-based), reason/notes. Source and output ranges must have equal lengths in this adapter; slow motion samples within these source handles. Same-track overlap is rejected; use separate tracks for explicit layering. Video input must contain enough handles, including slow clips. Audio ranges must fit the source.

Video properties: ZoomX, ZoomY, Pan, Tilt, RotationAngle, Opacity, using installed Resolve units. Video effects are an ordered array:

```json
[
  {"type":"camera","zoom":[[0,1.0],[179,1.08]],"center_x":[[0,0.5],[179,0.55]]},
  {"type":"opacity","keys":[[0,1.0],[150,1.0],[179,0.0]]}
]
```

Camera also accepts center_y and angle. Frame keys are clip-local output integers, strictly increasing, inside clip duration, at least two points. Camera center uses Fusion coordinates; zoom positive; opacity 0..1. One camera and one opacity effect per clip, combinable in chosen order. Curves use the existing helper's eased Bezier interpolation; this is not a universal interpolation engine.

Optional video retime: {speed:0.8,method:"flow",ramp_start:0,ramp_frames:0}. Methods flow/speedwarp; 0<speed<=1, optional lead-in and normal-to-slow ramp. Native retime precedes effects. These limits belong to this adapter only; accelerated/reverse/custom mappings need another implementation. Audio is not automatically retimed, moved or accelerated.

Audio optional fields: gain_db finite number, fade_in_frames/fade_out_frames within clip duration, layout mono/stereo. New48k/24-bit PCM assets are generated; original audio unchanged. Distinguish source mix intent from actual output gain/voice/channel checks.

## Mutation commands

- plan-register PLAN --workspace DIR selects the plan; validate/diff/locate remain read-only.
- produce PLAN --project NAME --timeline NEW_NAME --out NEW_DIR --preset NAME --save-current [--start] [--workspace DIR] builds and queues one preview. With --changes FILE --revision LABEL it first creates a new plan version.
- plan-apply is the separate build step; render-submit is the separate queue step.
- render-submit/produce accept --start-frame/--end-frame for timeline preview range, --width/--height for explicit preview size. --start launches only that queued task. No implicit waiting or automatic continuous viewing.
- render-status reads once. Check repeatedly within the active task when asked to complete a render; don't schedule an automation or treat queued as done.
- render-collect RECORD --out NEW_DIR [--file VIDEO] [--qc] [--observe] [--workspace DIR] checks completion and associates the actual video and hash. --qc/--observe only when appropriate to current requested review scope.
- review-record COLLECTION --input DECLARATION --out NEW_JSON [--workspace DIR] saves declared status accepted/changes_requested/skipped, required scope and observed_artifacts/user_feedback. It does not independently certify the declaration.
- operation-check OPERATION compares live work timeline structure/properties against the recorded fingerprint; not a full graph or color audit.

Build outputs: before.drp, editable.drp, native .comp files, generated audio, operation.json; keep their referenced media. A DRP is not a media archive. produce adds workflow.json and preview/render.json. Failure leaves partial assets and logs; inspect them before any retry. New output/name guards do not constitute automatic recovery.

## Feedback and state

plan-locate PLAN --start FRAME [--end FRAME] helps associate feedback with IDs. Generate changes with schema_version=1, base_sha256, original feedback, optional interpretation, preserve_ids and operations. Each operation has group=shots/audio, stable id, action=update/add/remove. Update set replaces whole fields, unset removes optional fields; add requires complete clip. No implicit ripple. Then plan-revise or produce --changes creates the next version.

--workspace maintains history, state and HANDOFF.auto.md; narrative remains in HANDOFF.md and creative-brief.md. New plans invalidate old preview associations. Actual collected files and review declarations are tied to plan hash and current render. A partial preview maps file frame0 to collection.timeline_range[0]; acceptance scope must remain explicit.

resume reads project context and detects missing references/external plan changes; it does not query live Resolve. Always distinguish saved state, actual execution, technical checks and artistic feedback.
