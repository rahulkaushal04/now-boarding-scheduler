# Now Boarding Scheduler

A weekly board-game session planner for [Now Boarding — Board Game Café](https://www.nowboarding.co.in), Bengaluru.

**Locations:**
[Now Boarding, HSR Layout](https://maps.app.goo.gl/x8mDruJ4M3BGVekBA) · [Now Boarding, Jayanagar](https://maps.app.goo.gl/5QBuavASgUroa1z79)

---

## What Is This Project?

Imagine you run a weekly board game group. You have 20 players, 15 different games, 6 possible time slots across the week, and 2 venues. Everyone has different preferences — some people can only make Tuesday evenings, others prefer weekends. Some games are owned by specific players, so they can't run without that person present.

**Now Boarding Scheduler** solves the puzzle of "who plays what, when, and where" automatically.

You upload the results of a simple poll (which games people want, when they're free, and where they can go), and the app produces a ready-to-use weekly timetable — picking the best sessions, explaining every decision in plain English, and showing you exactly why each game was chosen or skipped.

No spreadsheets. No manual coordination. Just upload and schedule.

---

## Why Does This Exist?

Coordinating board game sessions for a large group is harder than it looks:

- Not everyone wants to play the same game.
- Not everyone is free at the same time.
- Some games need a specific person present (the owner).
- You can only run so many tables at once in a single venue.
- Scheduling the same popular game every week leaves niche games forever unplayed.

Doing this by hand — even with a spreadsheet — is tedious, error-prone, and biased toward whatever comes to mind first. This app does it systematically, fairly, and transparently.

---

## How It Works (Simple)

The app is a **four-step wizard** that runs in your browser.

```
Step 1 → Upload your polls
Step 2 → Adjust game rules
Step 3 → See the recommended schedule
Step 4 → Check the insights
```

**Step 1 — Upload Your Data**
You upload four poll result files: which heavy games people want, which medium games they want, when they're available, and where they're willing to go. (You can also just paste the CSV data directly, or use built-in example data to try it out.)

**Step 2 — Game Rules**
The app detects game owners automatically. You can review and adjust things like minimum player counts, which days a game is allowed, or which venue it must be played at.

**Step 3 — Recommendations**
The app displays a timetable — rows are venues, columns are days. Each cell shows the game, the time, and how many players can make it. You also see "almost made it" games (high demand but couldn't fit) and games that couldn't be scheduled at all, with a plain-English reason for each.

**Step 4 — Insights**
Three questions answered: which games we're failing to serve, how HSR and Jayanagar compare, and which players got nothing this week.

---

## How It Works (Technical)

The scheduling engine is a three-layer pipeline. Layer 1 filters and
ranks candidates for display; Layer 2 makes every actual scheduling
decision via exact optimization (not a heuristic); Layer 3 explains the
result in plain English.

### Layer 1 — Filter & Rank Candidates (`engine/scorer.py`)

The app generates every possible combination of `(game, time slot, venue)` and applies **hard filters** first:

| Filter | Condition |
|--------|-----------|
| Allowed days | Game restricted to certain weekdays |
| Location lock | Game must run at a specific venue |
| Owner availability | Owner must be in the eligible player set |
| Minimum players | Eligible count must meet the game's floor |

Combinations that pass get a **display-only** weighted viability score
(demand, coverage, availability, popularity, diversity, location fit).
This score ranks near-miss suggestions and the "almost made it" /
"can't be scheduled" panels — it does **not** decide what gets
scheduled. That decision is made exactly, by Layer 2.

### Layer 2 — Exact Optimization (`engine/optimizer.py`, `engine/selector.py`)

Session selection is modeled as a mixed-integer linear program and solved
to a proven optimum with SciPy's HiGHS solver — not a greedy heuristic.
Two kinds of decision variables:

- **`x` (session runs)** — is `(game, slot, location)` scheduled at all?
- **`z` (player assigned)** — is a specific eligible player actually
  attending that specific session?

Splitting "eligible" from "assigned" is what lets the model enforce a
real physical fact exactly: a customer is one person and can only be at
one table at a time. Two games that both appeal to mostly the same
players at the same slot are no longer blocked by an arbitrary
similarity cutoff — the solver runs both and splits the shared audience
between them whenever that's worth doing, and leaves the second table
closed when it isn't.

**Hard constraints (never violated):**

1. Table ceiling per (slot, location) — physical table count, configurable per café.
2. Repeat limit per game per week.
3. One physical copy of a game can run at most once per slot, across every location.
4. A game can't switch cafés within the same day, even across different slots.
5. A player can be assigned to at most one session per slot.
6. A session's real assigned attendance (not just its eligible pool) must clear `min_players`.
7. A game's owner, if any, is assigned to every session of their own game.

**Objective — solved as six sequential MILPs**, each optimizing one
priority tier without ever giving back what an earlier, higher-priority
tier already achieved:

1. **Coverage** — maximize distinct customers served.
2. **Revenue** — maximize total attendance, weighted by each game's
   `revenue_weight` (a configurable per-head proxy — the poll data
   carries no price information, so this defaults to a neutral 1.0 for
   every game unless the café operator sets otherwise).
3. **Demand match** — among schedules already tied on coverage and
   revenue, prefer including the games more of the group actually voted for.
4. **Variety** — prefer a broader spread of distinct games.
5. **Parsimony** — prefer the fewest sessions that still deliver
   everything tiers 1–4 already locked in (never pad the schedule with
   a redundant, zero-value duplicate just because a table is free).
6. **Deterministic tie-break** — a canonical, upload-order-independent
   ordering so that even a genuine tie across every tier above always
   resolves to the same schedule.

Because each tier is solved to a *proven* optimum and only ever
constrains the next tier (never trades against it), the result is fully
explainable in business terms: "this schedule serves the most
customers; among those, it earns the most; among those, it best matches
what people voted for; among those, it's the most varied."

### Layer 3 — Explainability (`engine/explainer.py`)

Every selected session gets a structured reasoning trace:

- **Demand reason** — *"Kanban EV has 10 interested players — highest demand this week"*
- **Overlap reason** — *"6 of those 10 are free at Tuesday 6 PM and prefer HSR Layout"*
- **Selection reason** — *"Ranked #1. Covers 6 new players. Owner Grace is available."*
- **Conflict note** — *"Shares 3 players with Food Chain Magnate"*

This makes the schedule fully auditable — every decision can be traced back to the input data.

---

## Installation

### Prerequisites

- Python 3.11 or later
- `pip` (comes bundled with Python)

You do not need any special database, server, or cloud account. Everything runs locally in your browser.

### Step-by-step Setup

**1. Get the code**

```bash
git clone <repo-url>
cd now-boarding-scheduler
```

**2. Create a virtual environment** (recommended — keeps dependencies isolated)

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

This installs four libraries: `streamlit` (the web UI), `pandas` (data handling), `scipy` (the HiGHS MILP solver that powers the scheduling engine), and `pytest` (tests).

**4. Launch the app**

```bash
streamlit run app.py
```

Your browser opens automatically at `http://localhost:8501`. If it doesn't, open that address manually.

---

## Usage

### Quickstart (no data needed)

1. Run `streamlit run app.py`
2. On Step 1, tick **"Use example data"** in the right-hand panel
3. Click **Next → Game Rules**, then **Next → Recommendations**
4. Browse the schedule and click through to Insights

### Using Your Own Poll Data

#### What files do you need?

| File | Content |
|------|---------|
| `heavy_games.csv` | Poll results for complex/long games (3+ hours) |
| `medium_games.csv` | Poll results for lighter/shorter games (1–3 hours) |
| `timings.csv` | When each player is available |
| `place.csv` | Which venue(s) each player can attend |

#### CSV format

All four files follow the same structure: a `Name` column, then one column per option, with a `✓` character marking a vote. The last column is typically a `Total` and is ignored automatically.

**Heavy/Medium Games:**

```
Name,Bitoku,Food Chain Magnate,Kanban EV (courtesy Grace)
Victor,✓,,✓
Alice,,✓,✓
Grace,✓,✓,✓
```

> Game names written as `"Game Name (courtesy Player)"` are automatically parsed — the app detects that player as the game owner and adds the ownership constraint.

**Timings:**

```
Name,Tuesday, 6 PM,Wednesday, 6 PM,Saturday, 1 PM
Oscar,✓,✓,
Alice,✓,✓,
Victor,,,✓
```

**Locations:**

```
Name,HSR Layout,Jayanagar
Oscar,✓,
Alice,✓,
Victor,,✓
```

#### Input methods

On each tab in Step 1 you can:
- **Upload a file** — drag and drop or browse for a `.csv` file
- **Paste CSV** — copy from a spreadsheet and paste directly into the text box

#### Configuration options

| Setting | Default | What It Controls |
|---------|---------|-----------------|
| Max game repeats per week | 2 | How many times the same game can appear in the schedule (a rotation policy, not a physical limit) |
| Minimum players to run a game | 1 | Global floor; individual games can have higher requirements set in Step 2. Enforced against real assigned attendance, not just the eligible pool. |
| Max games at same time & place | 2 | How many tables can run simultaneously at one venue in one slot |

Two more knobs exist at the code level (not yet exposed in the UI, since
they need real numbers from the café operator rather than anything
derivable from poll data):

| Field (`models/config_model.py`) | Default | What It Controls |
|---|---|---|
| `tables_per_location` | `{}` (falls back to the setting above) | Per-café table count override, e.g. `{"HSR Layout": 3, "Jayanagar": 2}` |
| `revenue_weight_heavy` / `revenue_weight_medium` | `1.0` / `1.0` | Relative per-head revenue value of a session type, used only to break ties among otherwise-equal schedules. Neutral by default — the poll CSVs carry no price data, so raise one only if you know heavy sessions earn more per player (longer table time, more food/drink orders). |

### Downloading sample files

In Step 1, click **Download sample CSVs** to get a zip of all four example files. Use them as templates for your own polls.

### Running Tests

```bash
pytest
```

The test suite covers the CSV loader, entity builder, scorer, optimizer (MILP formulation and hard-constraint proofs), selector, and explainer. All tests run without Streamlit and complete in a few seconds.

### Comparing schedule quality

```bash
python scripts/evaluate_schedule.py
```

Runs the full pipeline against `example_data` and prints business metrics
(sessions, distinct games, real unique customers served, total assigned
attendance, unmet demand, suggestions) — useful for comparing algorithm
changes on identical input.

---

## Developer Notes

### Architecture

```
app.py                       Streamlit entry point — 4-step wizard, session state, engine orchestration
config.py                    Scoring weights and shared constants

data/
  loader.py                  CSV parsing → boolean DataFrames (handles vote markers, Total rows)
  processor.py               DataFrames → typed entities + derived indices (overlap map, demand/conflict matrices)
  validators.py              Cross-file consistency checks (players missing from timings / place polls)

engine/
  scorer.py                  Layer 1 — hard filters + 6-component display-only ranking score
  optimizer.py               Layer 2 — the MILP formulation: decision variables, hard
                              constraints, 6-stage lexicographic objective (see "How It
                              Works" above)
  selector.py                Layer 2 — thin wrapper: calls the optimizer, then chronological
                              ordering, "2nd table" badge, near-miss suggestions (display only)
  explainer.py               Layer 3 — structured plain-English reasoning traces per session

models/
  entities.py                Dataclasses: Player, Game, Slot, Location, CandidateSession
                              (eligible_players/eligible_count = demand pool;
                              assigned_players/assigned_count = the optimizer's real
                              post-conflict attendance), SelectionResult
  config_model.py            SchedulerConfig (user-facing settings with validation)

ui/
  upload_panel.py            Step 1 — file upload, paste, example data, stat counters
  game_rules_panel.py        Step 2 — @st.fragment data editor with visual diff and per-game reset
  recommend_panel.py         Step 3 — day × location timetable, suggestions, non-viable section
  insights_panel.py          Step 4 — demand, location, and coverage tables
  styles.py                  Dark-mode CSS, colour palette constants, HTML badge helpers

utils/
  names.py                   Name normalisation and fuzzy substring matching for owner detection

example_data/                Sample CSVs for local testing and the in-app "Use example data" toggle
scripts/
  evaluate_schedule.py       Standalone metrics report against example_data (no Streamlit)
tests/                       pytest unit tests — one file per engine/data module
```

### Key Design Decisions

**Exact optimization, not a heuristic.** Session selection is solved as a sequence of lexicographically-ordered MILPs via SciPy's HiGHS backend, each solved to a proven optimum (`mip_rel_gap=0.0`). The dataset is small (tens of games, a handful of slots and locations), so an exact global optimum is affordable, and it removes an entire class of "why didn't it pick the obviously better option" questions a heuristic can't answer.

**Player-level assignment variables.** Beyond deciding *whether* a session runs, the optimizer decides *which* eligible players are actually assigned to it, subject to one hard rule: nobody can be assigned to two sessions in the same slot. This is what replaced an earlier Jaccard-similarity heuristic that either fully blocked or fully allowed two audience-overlapping games at the same slot — the exact version simply lets the solver split the shared audience whenever that's the better outcome.

**Pre-indexed overlap map.** Rather than filtering players per candidate at score time, `build_overlap_map` pre-indexes players by game, slot, and location into three dicts and then intersects them. This drops the inner loop from O(players × games × slots × locations) to O(games × slots × locations) with cheap set operations.

**`@st.fragment` on the rules editor.** The data editor in Step 2 triggers a Streamlit rerun on every cell change. Wrapping it in `@st.fragment` scopes reruns to just that component, preventing the page from scrolling to the top on every keystroke.

**Near-miss suggestions.** After the optimizer runs, any game with zero scheduled sessions gets its best-scoring (Layer 1 score) candidate surfaced as a "suggestion" with a human-readable reason derived from the actual final schedule — making the result explainable not just for what was chosen but for what was left out.

**Scoring weights are display-only.** The six weights in `config.py` (`W_DEMAND`, `W_COVERAGE`, etc.) rank near-miss suggestions and the non-viable panel; they have no influence on which sessions actually get scheduled — that's governed entirely by the optimizer's hard constraints and lexicographic objective in `engine/optimizer.py`, which uses only values genuinely derived from the poll data (vote counts) or explicit business policy (`SchedulerConfig`).

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | 1.61.1 | Web UI framework |
| `pandas` | 3.0.5 | CSV parsing and DataFrame operations |
| `scipy` | 1.18.0 | HiGHS MILP solver (`scipy.optimize.milp`) for the scheduling engine |
| `pytest` | 9.1.1 | Unit testing |
