# Now Boarding Scheduler — Project Structure

**Repo:** `now-boarding-scheduler`
**App Title:** Now Boarding Scheduler

> **Stateless recommendation engine.** No database. Upload poll CSVs → set game rules (ownership, day restrictions, location locks) → get ranked session recommendations → accept/skip → export schedule. Dark mode only.

---

## Directory Tree

```
now-boarding-scheduler/
│
├── .streamlit/
│   └── config.toml             # Force dark theme + primary colour
│
├── app.py                      # Streamlit entry point — wizard flow, session state
│
├── config.py                   # Type aliases, constants, internal scoring weights
│
├── models/
│   ├── __init__.py
│   ├── entities.py             # Player, Game, Slot, Location, CandidateSession, SessionReasoning
│   └── config_model.py         # SchedulerConfig dataclass (target_sessions, max_tables, max_repeats)
│
├── data/
│   ├── __init__.py
│   ├── loader.py               # CSV parsing, validation, error collection
│   ├── processor.py            # Build overlap_map, demand_matrix, conflict_matrix
│   └── validators.py           # Cross-file checks, name normalisation
│
├── engine/
│   ├── __init__.py
│   ├── scorer.py               # Layer 1: score every candidate, apply game rules as hard filters
│   ├── selector.py             # Layer 2: greedy pick top N non-conflicting sessions
│   └── explainer.py            # Generate per-session reasoning traces
│
├── ui/
│   ├── __init__.py
│   ├── styles.py               # Dark mode CSS, colour constants, HTML helpers
│   ├── upload_panel.py         # File upload + session config (target, tables, repeats)
│   ├── game_rules_panel.py     # Editable game table: owner, allowed days, location lock
│   ├── recommend_panel.py      # Ranked cards with accept/skip + "Your Schedule" panel
│   ├── schedule_panel.py       # Final schedule summary + CSV/WhatsApp export
│   └── insights_panel.py       # Demand heatmap, coverage, conflicts, analytics
│
├── utils/
│   ├── __init__.py
│   └── names.py                # Name normalisation, fuzzy matching
│
├── tests/
│   ├── __init__.py
│   ├── test_loader.py
│   ├── test_processor.py
│   ├── test_scorer.py
│   ├── test_selector.py
│   └── test_explainer.py
│
├── sample_data/
│   ├── heavy_games.csv
│   ├── medium_games.csv
│   ├── place.csv
│   ├── timings.csv
│   └── game_metadata.csv
│
├── requirements.txt
└── README.md
```

---

## File Responsibilities

### Root

| File | Purpose |
|---|---|
| `.streamlit/config.toml` | Forces dark theme: `base = "dark"`, `primaryColor = "#00D4AA"`, `backgroundColor = "#0E1117"`, `secondaryBackgroundColor = "#1B1F27"`, `textColor = "#E6E6E6"`. |
| `app.py` | Streamlit entry point. Page title "Now Boarding Scheduler", icon ��, layout wide. Manages 4-step wizard (Upload → Game Rules → Recommendations → Insights) via `st.session_state["step"]`. Runs engine pipeline once on Step 2 → 3 transition, caches in session_state. |
| `config.py` | Type aliases (`PlayerId`, `GameId`, `SlotId`, `LocationId`). Constants: `VOTE_MARKER = "✓"`, `EXCLUDED_COLUMNS = {"Name", "Total"}`. **Internal scoring weights** (not UI-exposed): `W_DEMAND = 0.40`, `W_DIVERSITY = 0.20`, `W_COVERAGE = 0.20`, `W_POPULARITY = 0.10`, `W_AVAILABILITY = 0.05`, `W_LOCATION = 0.05`. |

### `models/`

| File | Contents |
|---|---|
| `entities.py` | `Player`, `Game` (with `owner`, `allowed_days`, `location_lock` fields), `Slot`, `Location`, `CandidateSession` (with `rejection_reason` for non-viable), `SessionReasoning`. Each has `to_dict()`. |
| `config_model.py` | `SchedulerConfig` with only 3 fields: `target_sessions` (default 4), `max_tables_per_slot` (default 1), `max_repeats_per_week` (default 1). `validate()` checks positive integers. No weight fields — weights live in `config.py` as constants. |

### `data/`

| File | Purpose |
|---|---|
| `loader.py` | One function per CSV type. Returns `tuple[pd.DataFrame, list[str]]`. Strips "Total" rows/columns, handles `✓` marker, quoted names. **Discovers all dimensions from column headers.** |
| `processor.py` | Builds entity dicts from DataFrames. `build_overlap_map()` — the core 3-way set intersection. `build_conflict_matrix()` — shared-player counts per game pair. **Auto-detects courtesy owners** from game name pattern `"Game (courtesy Player)"` and sets `game.owner`. |
| `validators.py` | Cross-file name validation, metadata coverage checks, `normalise_name()`. |

### `engine/`

**Zero Streamlit imports. Pure Python.**

| File | Purpose |
|---|---|
| `scorer.py` | **Layer 1.** `score_all_candidates(overlap_map, games, demand_matrix, slots, locations) → list[CandidateSession]`. For every (game, slot, location) triple: (1) apply game-rule hard filters — reject if owner missing, day not allowed, location locked elsewhere; (2) reject if below min_players; (3) compute 6-component weighted score using internal weights from `config.py`; (4) record `rejection_reason` for non-viable candidates. Returns all candidates sorted by score descending. |
| `selector.py` | **Layer 2.** `select_sessions(candidates, config, conflict_matrix) → list[CandidateSession]`. Greedy loop: pick highest-scoring viable candidate, enforce table capacity and repeat limits, apply coverage bonus and conflict penalty, stop at target. |
| `explainer.py` | `explain_candidate(candidate, context) → SessionReasoning`. Human-readable demand reason, overlap reason, selection reason, conflict note. Also generates `rejection_reason` strings for non-viable candidates. |

### `ui/`

**Dark mode. Premium feel. All charts use brand colours.**

| File | Purpose |
|---|---|
| `styles.py` | **Design foundation.** `inject_custom_css()` for dark-mode card styles, score bars, badges (accepted=mint, rejected=red), tag borders (heavy=teal, medium=gold). Exports colour constants: `PRIMARY = "#00D4AA"`, `ACCENT = "#FFB830"`, `ALERT = "#FF6B6B"`, `SUCCESS = "#69F0AE"`, `SURFACE = "#1B1F27"`, `SURFACE_RAISED = "#262B36"`, `BORDER = "#2D333B"`, `TEXT = "#E6E6E6"`, `TEXT_SEC = "#9CA3AF"`. Helper functions: `score_bar_html(score)`, `badge_html(text, color)`. |
| `upload_panel.py` | `render_upload_section() → tuple[dict[str, UploadedFile|None], SchedulerConfig]`. Five file uploaders + 3 number inputs (target sessions, max tables, max repeats). Data preview, validation feedback, summary card. Returns uploaded files and config. |
| `game_rules_panel.py` | **NEW — the key UI panel.** `render_game_rules(games, players, slots, locations) → dict[GameId, Game]`. Displays an editable table with one row per discovered game. Columns: Game Name (read-only), Weight Class (read-only), Min Players, Max Players, Owner (dropdown: player names + "None"), Allowed Days (multi-select: discovered days, default all), Location (dropdown: discovered locations + "Any"). Pre-populated from metadata + auto-detected owners. Returns updated Game dict with all rules applied. Uses `st.data_editor` or `st.columns` with individual widgets per row. |
| `recommend_panel.py` | `render_recommendations(candidates, all_players) → list[CandidateSession]`. "Your Schedule" panel at top (accepted sessions, live coverage counter). Below: ranked dark-surface cards — game name, weight-class badge, slot, location, eligible count, score bar, expandable reasoning, Accept/Skip buttons. Non-viable candidates in collapsed "Not viable" section with reasons. |
| `schedule_panel.py` | `render_final_schedule(accepted)`. Summary grid of accepted sessions. `st.download_button` for CSV. Copy-paste text block for WhatsApp ("�� Game | �� Day Time | �� Location | �� X players"). |
| `insights_panel.py` | `render_insights(candidates, players, games, demand_matrix, conflict_matrix)`. All charts use `plotly_dark` template + brand colours. Demand heatmap, game ranking bars, conflict matrix, player coverage, location split donut, unviable games list, time slot density bars. |

### `utils/`

| File | Purpose |
|---|---|
| `names.py` | `normalise(name) → str`. `find_best_match(name, candidates) → str|None`. |

### `tests/`

| File | Covers |
|---|---|
| `test_loader.py` | CSV parsing: Total filtering, ✓ markers, quoted names, empty files. |
| `test_processor.py` | Overlap map correctness, conflict matrix symmetry, courtesy owner detection. |
| `test_scorer.py` | Scoring components [0,1], viability gate, game-rule filters (owner, day, location). |
| `test_selector.py` | Table capacity, coverage bonus, conflict penalty, stops at target. |
| `test_explainer.py` | Reasoning traces generated, rejection reasons correct. |

---

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Files | `snake_case.py` | `game_rules_panel.py` |
| Classes | `PascalCase` | `CandidateSession` |
| Functions | `snake_case` | `build_overlap_map()` |
| Constants | `UPPER_SNAKE` | `W_DEMAND`, `PRIMARY` |
| Type aliases | `PascalCase` | `PlayerId`, `GameId` |
| Session state keys | `prefix_name` | `upload_files`, `engine_candidates`, `accepted_indices` |
| Test functions | `test_<what>_<condition>` | `test_scorer_rejects_missing_owner` |

---

## Dependency Flow

```
app.py
  ├── ui/*              (presentation + styling)
  ├── data/*            (parsing + indexing)
  ├── engine/*          (scoring + selection)
  ├── models/*          (shared data structures)
  └── config.py         (constants + internal weights)

ui/styles.py            (imported by all ui/* modules)
ui/* → models/*         (reads entities for display)
data/* → models/*       (constructs entities)
engine/* → models/*, config.py  (operates on entities, reads weights)
```

No circular dependencies. `models/` depends on nothing. `engine/` depends on `models/` and `config.py`. `data/` depends on `models/`. `ui/` depends on `models/`. `app.py` orchestrates all.

---

## Key Design Decisions

1. **UI/UX is top priority. Dark mode only.** Electric teal + warm gold on dark surfaces. Premium, modern feel.
2. **Game Rules Editor replaces weight sliders.** The owner thinks in "Kiran owns Kanban EV" and "FCM only on weekends" — not "set w_demand to 0.4". Concrete constraints, not abstract tuning.
3. **Scoring weights are internal.** Baked into `config.py` at sensible defaults. Not exposed in UI. Owner controls outcomes through game rules and session config.
4. **Only 3 configurable numbers.** Target sessions, max tables per slot, max repeats. Everything else is either auto-detected or set via game rules.
5. **Recommendation engine, not auto-scheduler.** Owner accepts/skips. FCFS after publishing.
6. **Demand-overlap scoring + greedy selection.** ~240 candidates, sub-millisecond. No solver dependencies.
7. **Engine is pure Python.** Zero Streamlit imports. Testable independently.
8. **Fully stateless.** No database. Fresh CSVs every week.
9. **All dimensions dynamic.** Discovered from CSV headers/rows.
10. **Courtesy owners auto-detected.** Parsed from game name pattern, editable via Game Rules UI.