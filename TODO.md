# TODO — Reproducible code export

Tracking follow-ups to the reproducible-code-export work. See the plan at
`/root/.claude/plans/pull-the-latest-version-resilient-crescent.md` for full
context.

## Determinism gaps in `process-improve`

- [ ] Open upstream issue on `kgdunn/process-improve`: add a `seed: int | None = None`
      kwarg to `generate_design` and any RSM / randomized-run-order routines,
      threaded through `numpy.random.default_rng(seed)`. Without this, the
      downloaded script cannot reproduce run-order randomization.
- [ ] Once the upstream `seed` kwarg ships, bump the pinned `process-improve`
      version in `reproducible_export_service.py` and have the exporter
      inject a synthesized seed when the original `tool_input` omitted one,
      recording it in the generated README so the original run can be
      replayed exactly.
- [ ] Document in `process-improve` which tools are already deterministic
      (no RNG at all) vs. which depend on a seed. The exporter should key
      off that list rather than hard-coding assumptions.

## ~~Pre-existing CI failures (unrelated to reproducible-code-export)~~

- [x] ~~`tests/test_simulator_flow.py::test_loop_*` fail with
      `KeyError: 'sim_id'`~~ — **resolved 2026-04-23**. Root cause was
      that `process-improve==1.5.1` (the pinned version) didn't ship the
      `simulation/` module, so `execute_tool_call("create_simulator", …)`
      raised `ValueError: Unknown tool`, which became an `is_error`
      tool_result with no `sim_id` key. PR #73 added a skip guard;
      `process-improve 1.6.0` (released in `kgdunn/process-improve#103`)
      now ships `simulation/`; this PR bumps the pin to `>=1.6.0` and
      drops the skip guard. All three tests now run and pass.

## Factorial backend

- [ ] When the analysis pipeline starts fitting models against
      `experiments.results_data`, drop rows where `included == false`
      before passing the data to `process-improve`. The frontend's
      Results Entry form (PR #119) already records the per-row
      `included` flag (default `true`) and `notes`; the flag is
      currently stored as metadata only and the analysis path does
      not yet read it.
- [ ] Populate `ToolCall.tool_version` per call in
      `backend/src/app/services/agent_loop.py` (field exists on the ORM but
      is currently left null). Lets the exporter pin per-call version when
      an experiment spans a library upgrade.
- [ ] Guard `fetch_analysis_tool_calls` against `output_truncated=True` rows
      — refuse export and surface the call(s) in the error. The flag is
      never set true today but the guard should land before anyone adds
      truncation logic later.
- [ ] Decide on public-share exposure of reproducible bundles in
      `backend/src/app/api/v1/endpoints/shares_public.py`. Default:
      unauthenticated viewers do NOT get `?format=zip` / `py` / `ipynb` /
      `md_code` (raw response data). Revisit if users ask for "public,
      reproducible" sharing.
- [ ] Consider extending the `ExportMenu.svelte` PDF `acknowledge_share`
      gating pattern (`experiments.py:286`) to the bundle, since it also
      embeds raw response data.
- [ ] HTML-escape user-supplied strings in `email_service.py` templates.
      `send_signup_confirmation` and `send_admin_notification` interpolate
      `use_case` (and `signup_email`) directly into HTML via f-string with no
      `html.escape(...)`. A submitter could land tags / scripts in the
      admin-facing email. Low blast radius (admin reads in their own client,
      not on a Factorial domain) but worth fixing as a single pass across the
      file.

## Plot reproducibility

- [ ] Scope in docs (`docs/architecture/`): the guarantee is **numerical**
      equivalence of tool outputs, not byte-identical plots. Mention font /
      renderer drift.
- [ ] Investigate pinning `matplotlib` + a bundled font in the generated
      `requirements.txt` to tighten plot determinism. Probably not worth it
      — call it out and move on unless users ask.

## Data bundle

- [x] ~~Large `tool_output` objects (full design matrices, plot payloads) go
      into `./fixtures/tool_output_<n>.json` in the zip~~ — retired in PR-2
      (2026-04-23). The runnable path embeds `tool_input` via `json.dumps`
      and regenerates `tool_output` on re-run, which is both simpler and a
      stronger reproducibility check than a frozen-fixture diff.
- [ ] Include a `check_outputs.py` in the bundle that re-runs the script
      and diffs against the agent's recorded `tool_output` so users can
      verify numerical reproducibility without reading the code. (Would
      need a separate "recorded outputs" JSON inside the bundle.)

## Docs

- [x] Add a short section under `docs/architecture/` describing the
      reproducibility guarantee, scope limits, and the TODO items above so
      the scope is visible without digging through code. (Landed as
      `docs/architecture/reproducibility.md` in PR-2.)
- [ ] Link to the generated bundle's README.md from the main docs so users
      can preview what they'll get before clicking download.

## Phased delivery

- [x] **PR-1 — MINOR bump.** `.py` export + `reproducible_export_service.py`
      + round-trip tests. Ships via the existing `GET /export?format=py`
      endpoint. No UI.
- [x] **PR-2 — MINOR bump.** `.ipynb`, `.md_code`, `.zip` bundle,
      `data.xlsx`, `README.md`, `requirements.txt`. Add `nbformat`
      dependency. Bundle tests.
- [x] **PR-3 — PATCH bump.** `ExportMenu.svelte` entries + `types.ts` enum
      sync + section split. No backend change.

## DOE upload tool — chat agent integration (deferred)

The current upload feature (PR #81) ships:
- `POST /api/v1/experiments/uploads` + `/answers` + `/finalize` REST surface
- `app.services.upload_parsing_service` (xlsx/csv → 2D matrix)
- `app.services.upload_claude_service.discover_structure` (forced tool_use,
  two tools: `report_design_structure` / `ask_clarifying_questions`)
- Frontend wizard + reusable `<ExperimentDataTable>` + `<DataTableModal>`
  with F2 keyboard shortcut

What is **not** yet wired and should follow up:

- [ ] Register `parse_uploaded_design` as a tool the chat agent can invoke.
      Input shape `{rows: list[list[Any]]}` so a user pasting CSV-like text
      into chat gets the same parsing behaviour. Implementation sketch:
      add a `_LOCAL_TOOL_HANDLERS` registry to
      `backend/src/app/services/tools.py`; have `execute_tool_call`
      dispatch local handlers before falling through to
      `process_improve`; expose `discover_structure` via a sync wrapper
      that can be called from the agent thread.
- [ ] File-attachment plumbing through the chat endpoint
      (`backend/src/app/api/v1/endpoints/chat.py`). The chat endpoint
      currently accepts JSON-only message turns; adding multipart
      attachments + a transient cache keyed by `file_id` is its own
      side quest. Agree with the user on UX before doing this.
- [ ] Frontend: surface the chat tool's clarifying-question output via
      the existing `ToolResultCard.svelte`, and route attachments
      from `ChatWindow.svelte` into the new endpoint.

## Frontend — mobile

- [ ] Replace the top-nav link group in `frontend/src/routes/+layout.svelte`
      with a hamburger drawer on small screens. The current patch hides the
      balance span and the display-name span under `sm:` so the row fits on
      a phone; a drawer would surface them again without wrapping.

## Chat agent latency (follow-ups from PR #99)

- [ ] Once we have a few weeks of `logs/timing.jsonl` data, decide whether
      to surface the per-phase breakdown in the UI (debug overlay or admin
      page). The current per-step `1m 0s` badge is enough for casual users;
      this is engineering instrumentation only.
- [ ] Replace the per-event `INSERT … COMMIT` in
      `app.services.agent_service._persist_chat_event` with a single
      `executemany` per turn (or move to a per-turn snapshot row) once the
      timing log shows DB write latency is still material after the
      token-batching landed.
- [ ] Replace the `await asyncio.sleep(0.01)` busy poll in
      `app.services.agent_service._stream_from_queue` with an
      `asyncio.Queue` (or a thread-safe bridge) so the SSE generator wakes
      on the next event instead of polling. Worth measuring first via the
      timing log to confirm the poll latency is actually visible.

## Gutting the pre-launch scaffolding (PR #142)

Factorial never launched, and roughly half the backend was infrastructure
built for a user base that does not exist. PR #142 removed the first tranche.

Landed:

- [x] Neo4j (`app/graph/`, the container, volume, healthcheck, three settings
      and the startup connectivity check). The DOE knowledge it was meant to
      hold lives upstream in `process_improve.experiments.knowledge` as
      versioned YAML.
- [x] GeoIP (`geoip_service`, `GEOIP_COUNTRY_DB_PATH`, the `maxminddb`
      dependency).
- [x] BYOK in full: four services, the credentials-history table, six columns
      on `users`, two on `sessions`, `messages.byok_used`, the crypto
      dependencies, the frontend section and badge, and the docs page.
      Migration `0012`.
- [x] The hosted MCP REST shim, `tool_budget`, and the `tool_usage` table.
      Migration `0013`.

Still to remove, in rough order of value:

- [x] Balance / metering: `balance_service`, `user_balance`, the admin
      top-up endpoint and UI, and the balance fields on `/auth/me`.
      Migration `0014`. `pricing` and the per-message cost columns are
      deliberately **kept**: they are telemetry, not billing, and they answer
      "what is the agent spending per turn" whether or not anyone is charged.
- [ ] Invite-based signup: `signup_service`, `setup_token_service`,
      `signup_requests`, `setup_tokens`, the admin approve/reject endpoints
      and the `/register` flow. Replace with a waitlist row plus
      admin-created accounts, or magic-link login.
- [ ] The sqladmin browser (`app/admin/`, `mount_admin`, `itsdangerous`,
      the separate admin session cookie) and the `admin_events` table with
      its hourly LLM-performance snapshot loop in `main.py`.
- [ ] `anthropic_status` (244 LOC) feeds the public `/health/llm` banner.
      Keep or drop is a product call, not scaffolding: decide with the user.
- [ ] ~~`simulator_interception`, `turn_timing`~~ - **retired 2026-08-07,
      do not remove these.** Listed here in haste; both turn out to be
      load-bearing. `simulator_interception` provides the `pre_dispatch` /
      `post_dispatch` hooks the agent loop uses to drive the fake-data
      simulator, which is a real teaching feature, not scaffolding.
      `turn_timing` writes `logs/timing.jsonl`, which the "Chat agent latency"
      items below explicitly depend on having a few weeks of data from.

**Do not remove `roles`.** It looks like RBAC and is not: `is_admin` is the
RBAC flag, while the `roles` table holds the user's *professional profile*
(`chemical_engineer`, ...) which is interpolated into the agent system prompt
as `user_background` (see `_ALLOWED_BACKGROUND_RE` in `agent_service.py`).
Dropping it would degrade the agent's personalisation. This was in the
original plan for PR #142 and was removed from it after reading the code.

## Second distribution channel (process-improve #485)

- [ ] Once `doe-designer` ships, decide what the hosted app offers that the
      skill does not, and cut the rest. Current answer: persistence across
      sessions, results entry by someone without a Claude account, sharing,
      and the reproducible-export bundle.
- [ ] Reproduce the Vazquez et al. (2026) benchmark (36 tasks, 8/16/32 runs,
      4-26 factors) against Claude plus the process-improve tools, now that
      `moment_aberration` can score any two-level matrix. Expected result is
      100% minimum aberration on every task, because the design comes from a
      catalogue rather than from the model. Good launch material for both
      channels.

## Design comparison evaluator

Side-by-side design comparison: designs as columns, evaluation metrics as rows.

- [ ] `POST /designs/compare` — takes factor specs plus a list of candidate design
      requests, generates each, runs `evaluate_design` over a shared metric list,
      and returns a metric-by-design grid. Saved experiments are a special case
      (pass ids instead of specs), not the primary shape: the useful moment is
      *before* runs are committed, comparing "8-run vs 16-run vs DSD" for the
      same factors.
- [ ] Frontend `DesignComparisonTable.svelte`. Metrics down, designs across.
      Highlight the winner per row.
- [ ] **Mark metrics that are not comparable across sizes.** D-efficiency across
      different run counts flatters the bigger design almost by construction.
      `moment_aberration` already refuses cross-size comparison (`is_better_than`
      raises); the table must be equally honest rather than quietly ranking.

## Partial-results monitoring ("the reading strip")

An agentic monitoring surface for a design whose results are still arriving.
Mockup and settled spec: https://claude.ai/code/artifact/5890310e-fcb3-46e9-a509-287a04fddc06

Backend:

- [ ] Partial-analysis service: given a design plus the results entered so far,
      report (a) what is estimable now, (b) what the next N runs would make
      estimable, (c) what must not be concluded yet. Three things make this
      statistically non-trivial and they are the whole point:
      - the model may not be estimable at all yet (rank-deficient model matrix)
        and must say so rather than returning a confident fit;
      - a partial set is **not a random subset** — runs arrive in run order, so
        any trend is confounded with time;
      - the design's orthogonality only exists once it is complete.
- [ ] **Read the `included` flag.** Already recorded per results row (PR #119) and
      still ignored by the analysis path. Excluding a suspect run is exactly what
      the strip's alert state offers, so the two belong in one piece of work.
      (Supersedes the older standalone item above.)
- [ ] **Persist the reading, do not compute it on demand.** Written alongside the
      experiment whenever results change. Two reasons: owner and viewer then see
      the same words, and it keeps tool execution off the unauthenticated public
      share route.
- [ ] Expose it on `shares_public.py` so viewers get it too.

Frontend:

- [ ] `ReadingStrip.svelte` on `/experiments/[id]`, between the design matrix and
      the results table. States: silent / collapsed / expanded / alert.
      `SystemBanner.svelte` is the existing precedent for the shape.
- [ ] Mobile: expanded is a **bottom sheet**, not an inline expansion, so actions
      sit under a thumb. Dismiss by swipe; resting state is a small badge on the
      Results header so the feature does not appear to vanish.

Decisions (2026-08-22, confirmed with @kgdunn):

- **Dismissal is per device** — `localStorage`, keyed to a hash of the current
  reading, so a changed reading returns. No table, no schema change, no sync.
  Explicitly the cheap option.
- **Everyone sees it, viewers included.** Shared-experiment viewers get the
  reading; the notes are the context they most need.
- **The alert never blocks.** It flags the row and offers to exclude it; results
  entry always succeeds. A run that breaks the pattern is sometimes just an
  interesting result.
- **No F2 / keyboard shortcut for now.** Click the row to expand, `Esc` to
  dismiss. Undiscoverable, collides with screen readers and browser defaults,
  and the resting badge is the affordance worth spending on instead.
