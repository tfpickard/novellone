# Changes Summary – Content Axes & Cover Backfill Automation

## Overview
The platform now treats narrative tone as a first-class primitive. Ten configurable content axes sit alongside the existing chaos sliders, informing premise generation, chapter pacing, cover imagery, analytics, and admin tooling. In parallel, the background worker gained an automated cover-art backfill loop so completed stories no longer languish without visuals.

## What’s New

### Structured content controls
- Added JSONB columns and SQLAlchemy mappings for story-level content settings and chapter-level readings.
- Normalised ten named axes (sexual content, violence, strong language, drug use, horror & suspense, gore, romance focus, crime, political themes, supernatural elements) with average level, momentum, and premise remix multiplier controls.
- Extended runtime configuration to validate and persist axis edits, exposing them through the admin API and client.
- Expanded the axis catalog with cosmic horror, bureaucratic satire, and archival glitch defaults so prompts and analytics can lean into stranger registers out of the box.

### Prompting, storage, and telemetry
- Story generation now seeds OpenAI prompts with per-axis expectations, captures chapter feedback, and clamps malformed responses before persisting.
- WebSocket broadcasts and REST payloads surface the content metrics so live clients and dashboards stay in sync.
- Stats and recommendation feeds aggregate axis averages alongside chaos readings for richer analytics.
- Premise prompt directives refresh more aggressively (see environment defaults) and now rotate through a larger pool of sample titles to keep the seeds feeling new.

### Frontend UX updates
- Introduced shared metadata helpers so all Svelte views consume consistent axis definitions and defaults.
- Admin configuration page exposes editable controls for each axis plus cover backfill cadence knobs, with inline validation.
- Story detail, timeline, and stats dashboards visualise axis targets and chapter readings via badges, tables, and radar/timeline augmentations.

### Automated cover-art recovery
- Background worker schedules periodic passes that batch-generate covers for any completed stories missing imagery, with guardrails to avoid concurrent runs.
- Admin endpoints and UI now report worker status, allow cadence changes, and expose a manual trigger for on-demand backfills.
- Environment templates document the new cadence variables for production and Railway deployments.

## Testing & Verification
- Backend: `pytest backend/tests -q`
- Frontend build: `npm run build`
- Frontend unit suite currently surfaces a known failure (`npm test`) caused by upstream component tests expecting historic API shapes; follow-up fixes are planned.
