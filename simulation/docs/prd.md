PRD — Phase 2: Live Demo-Ready Urban Intelligence Platform
Status: Draft for team review
Owner: Tushar (integration / SUB-05)
Target demo date: 2026-07-18 (4 weeks out)
Authority: Below PROJECT_SPEC (1).md and DECISIONS.md; above subsystem READMEs.

1. Background — where we are today
Phase 1 has landed. The repo on main contains:

A working FastAPI + WebSocket backend (SUB-05) with the full lifecycle, REST, WS, snapshot, metric, event-injection, and CSV export endpoints.
A working Pravaah dashboard (SUB-06) that talks to the backend over REST + WS, with auto-injected archetypal events, live grid heatmap, Reset/Export buttons, and an AQI card (PRs #36, #37, #41).
A mesa-backed simulation core (SUB-01) with Phase 1 AI: economic agents, calibration module, multi-leg scheduling, transit agents (PR #39).
A Delhi data pipeline (SUB-04) — OSM network, weather, census population, validation CSVs.
Agent behavior scaffolds (SUB-02) with retail, transit, mitigation, and demand-curve agents.
Transport routing primitives (SUB-03) — BPR congestion model, multi-modal transfer routing, path cache.
What's missing: the mesa engine has never been run end-to-end against real Delhi data through the live backend with the dashboard rendering it. Every subsystem works in isolation; nothing has been demonstrated as one stack.

That's what Phase 2 is for.

2. Goal — what success looks like
A teammate or stakeholder can clone the repo and, within 5 minutes, run a live demo of three calibrated scenarios — monsoon, metro shutdown, fuel shock — against the real mesa engine on real Delhi data, with the dashboard rendering distinct dynamics for each, and download any run as a CSV.

Concrete success metrics:

Metric	Target
M1	Time-to-demo from fresh clone	≤ 5 min on a laptop
M2	Mesa engine baseline output (no events)	within ±20% of published DMRC ridership and road-congestion stats
M3	Each scenario	produces visibly distinct dynamics over 100+ ticks
M4	Full demo (3 scenarios + 1 export)	runs without UI/console errors
M5	A scenario's CSV export	round-trips through pandas with no schema warnings
M6	Deployed demo URL (optional)	exists and serves all 3 scenarios
If any of M1–M5 fails on demo day, we ship Phase 2 anyway; M6 is bonus.

3. Non-goals — what we're explicitly not doing this phase
Multi-city support (Delhi only — _CITY_CENTER stays delhi).
LLM at simulation runtime (spec §4.3 — non-negotiable).
Authentication beyond a single optional read-only API key.
Mobile / responsive frontend.
Postgres or Redis — SQLite + in-process only.
Postpone: bike lanes, freight, pollution beyond AQI, ride-hail surge.
4. Functional requirements per subsystem
Each subsystem ships one focused PR per row. Acceptance criteria are checkboxes that map directly to test cases.

SUB-01 — Simulation Core (purav)
Deliverable	Acceptance
1.1	Calibrate mesa engine baseline against published Delhi commute stats	Mesa run with default scenario_a config produces avg_commute_minutes ∈ [25, 42], metro_load_pct ∈ [25, 70] at peak, road_congestion_index ∈ [0.2, 0.8]
1.2	Deterministic seed contract	Two runs with same config + seed produce byte-identical metric arcs (assert in test_simulation.py)
1.3	First-class mesa end-to-end CI step	New .github/workflows/sim-e2e.yml: boot backend with BACKEND_SIM_ENGINE=mesa, tick 100 times, assert metrics non-trivial
1.4	Document baseline behavior	simulation/CALIBRATION.md records expected output ranges and the published sources
SUB-02 — Agent Behavior (shubham)
Deliverable	Acceptance
2.1	Income-stratified mode elasticity	Fuel shock event drops mode_share.car by ≥ 30% in low-income agents within 50 ticks; ≤ 10% in high-income
2.2	Agent route/mode memory	Agents who hit denied boarding 3× pick alternate mode next day; visible as gradual share shift in metro-shutdown scenario
2.3	Festival demand spike event	New EventType.DEMAND_SPIKE honored by agents (boost commute volume by config-given %); contract change coordinated with SUB-05
SUB-03 — Transport Routing (Sarthak, purav)
Deliverable	Acceptance
3.1	Real DMRC frequency schedule	simulation/data/dmrc_schedule.json with peak/off-peak frequencies per line; sourced from DMRC public timetable
3.2	Boarding capacity constraints	When metro_load_pct > 100, new boarders queue (added wait minutes) or get denied → reroute via bus; surfaces as visible queue/denial in metro-shutdown
3.3	Bus bunching emergent property	Bus arrivals show realistic spacing variance (CV ≥ 0.3 measured over 100 ticks)
SUB-04 — Data Engineering (Bham)
Deliverable	Acceptance
4.1	IMD weather API integration	data/scripts/fetch_weather.py pulls today's Delhi forecast from IMD endpoint, writes weather_delhi.csv; cache 12 h
4.2	Synthetic population validation	New tests/test_population_validity.py: χ² of synthetic age × income × HH-size against census marginals; pass at p ≥ 0.05
4.3	Data lineage doc	data/LINEAGE.md lists source → script → output for every Parquet file
4.4	DVC or git-lfs for processed Parquet	One-command make data reconstructs processed_data/ from sources
SUB-05 — Backend & Integration (Tushar)
Deliverable	Acceptance
5.1	Parquet tick history persistence	StateStore appends per-tick aggregates to data/runs/{scenario_id}.parquet; survives restart
5.2	/api/v1/compare?scenarios=a,b&metrics=… endpoint	Returns aligned time-series for N scenarios on a single metric set
5.3	Event log endpoint	GET /api/v1/scenarios/{id}/events returns SQLite-persisted history of injected + auto-injected events
5.4	Daily CI smoke schedule	backend-ci.yml runs test_ws.py on a daily cron and posts failures to Slack
5.5	Reconcile root scaffold	Root docker-compose.yml, .env.example, README.md align with spec (SQLite, Vite, no LLM); docker compose up works from root
SUB-06 — Frontend (achal, Tushar)
Deliverable	Acceptance
6.1	Sparkline charts in 5 stat cards	Each card draws a 60-tick rolling sparkline; updates smoothly at 1 tick/sec
6.2	Comparison view backed by /compare	Compare button fetches two scenarios, renders side-by-side metrics
6.3	OSM tile basemap behind canvas	Leaflet layer renders Delhi; heatmap aligns with real geography
6.4	Custom scenario builder	Form posts POST /scenarios with seed, population, params; new scenario appears in selector
6.5	Event injection UI	Three buttons (weather / infra / policy) with slider inputs; sends real POST /events
AI services (offline only — needs owner)
Deliverable	Acceptance
7.1	NL → ScenarioConfig generator	CLI tool reads a sentence, emits a ScenarioConfig + initial events JSON; pre-compute only, never runtime
7.2	Run explainer	CLI tool reads a finished run's CSV, emits a 200-word plain-English summary of what happened and why
Integration / DevOps (Tushar)
Deliverable	Acceptance
8.1	Playwright E2E	One headless test: start backend + frontend, expect "Live Connected" badge + tick-5 metrics non-zero
8.2	Deploy backend to Railway, frontend to Vercel	Public URL serves all 3 scenarios; survives 1 h continuous use
8.3	Recorded fallback demo	5-minute screen recording of the live stack; checked into docs/demo/
5. Non-functional requirements
Performance: Tick loop sustains ≥ 1 tick/sec at 5,000-agent population on a 2024-era laptop.
Latency: Policy slider → next-tick metric change ≤ 2 ticks (≤ 2 s wall-clock).
Determinism: Same config + seed → byte-identical metric arc.
Single-laptop demo: PROJECT_SPEC §4.3 — non-negotiable.
Cloud spend: < ₹10,000 total for the deployed demo (Railway hobby + Vercel free).
No LLM at runtime: PROJECT_SPEC §4.3 — non-negotiable. AI lane in §4 is pre-compute only.
6. Wire contract (frozen for Phase 2)
The frontend depends on these shapes. Breaking changes require coordinated PRs across SUB-01, SUB-05, SUB-06 and a DECISIONS.md entry.

AggregateMetrics: tick, sim_time_minutes, rain_intensity, avg_commute_minutes, mode_share (dict by Mode), metro_load_pct, bus_load_pct, road_congestion_index, agents_commuting, aqi_estimate
Mode enum: walk, bike, bus, metro, auto, car, bike_share, e_rickshaw
TickDiff: scenario_id, tick, metrics, changed_cells
ScenarioConfig, Event, EventType — unchanged from current
EventType may add DEMAND_SPIKE (SUB-02 task 2.3) — additive only
7. Dependencies & sequencing

Week 1: SUB-04 data ready ─┐
                           ▼
Week 2: SUB-01 mesa baseline ──► SUB-05 mesa end-to-end CI
                           ▼
Week 3: SUB-02 + SUB-03 behavioral fidelity
                           ▼
Week 4: SUB-06 UI polish + Integration deploy + recorded fallback
Items that can run in parallel any time: SUB-05 root scaffold reconciliation (5.5), SUB-04 lineage doc (4.3), SUB-06 sparklines (6.1).

8. Risks & mitigations
Risk	Mitigation
R1	Mesa engine too slow at 5,000 agents	Profile early (week 2); if needed, drop default population to 2,500 — calibration still valid
R2	Real Delhi data needs cleaning	SUB-04 starts week 1; data team flags blockers to SUB-01 immediately
R3	AI services lane orphan	If no owner picked by end of week 1, drop AI lane and document as Phase 3
R4	Demo network fails	Recorded fallback (8.3) is non-optional
R5	Wire contract drift between SUB-01 and SUB-05/06	This PRD §6 freezes it; any change is a coordinated PR
R6	CI red for > 1 day	SUB-05 owns the daily smoke (5.4); whoever broke it owns the fix
9. Milestones
Week ending	Milestone	Owner
Week 1 (2026-06-27)	Real Delhi data ready + lineage doc + root scaffold reconciled	SUB-04, SUB-05
Week 2 (2026-07-04)	Mesa engine first end-to-end run in CI; sparklines in dashboard	SUB-01, SUB-05, SUB-06
Week 3 (2026-07-11)	Calibration round 1; income elasticity + boarding capacity working	SUB-01, SUB-02, SUB-03
Week 4 (2026-07-18)	Deploy + Playwright E2E + recorded fallback; DEMO READY	All
10. Open questions (need decisions before Week 1 standup)
Who owns the AI services lane? Two small offline tools, but needs a name.
Deploy target — Railway or Render? PR description in backend/README.md recommends Railway (stays warm); team poll.
Demo audience — internal team or external stakeholders? Affects polish budget for SUB-06.
Should we adopt feature-flag-style gating (Phase 2 work behind BACKEND_PHASE=2) or merge directly?
PR review SLA — within 24 h? Needed because four streams are in flight.
11. Out of scope (parking lot for Phase 3)
Multi-city support
True mid-run branch (deep-copy engine state)
Bicycle-lane separate routing graph
Heat / smog coupling beyond rain
Real ride-hail surge dynamics
Festival demand spike beyond the basic event hook
AI-driven policy suggestion
Light theme + Hindi i18n
WebSocket resume-on-reconnect
12. Sign-off
Subsystem	Owner	Sign-off (date)
SUB-01	purav	
SUB-02	shubham	
SUB-03	Sarthak / purav	
SUB-04	Bham	
SUB-05	Tushar	
SUB-06	achal / Tushar	
AI services	TBD — open question #1	
Integration / DevOps	Tushar	
How to use this doc
Each row in §4 is one PR. The acceptance criteria are the test plan.
Wire contract §6 is frozen — if you need to change it, post in the channel before you start the PR.
Risks in §8 — flag them in standup the moment you see one materialising.
Open questions in §10 need answers by Week 1 standup; without those, several rows in §4 can't start.