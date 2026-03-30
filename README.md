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
Step 4 → Explore the analytics
```

**Step 1 — Upload Your Data**
You upload four poll result files: which heavy games people want, which medium games they want, when they're available, and where they're willing to go. (You can also just paste the CSV data directly, or use built-in example data to try it out.)

**Step 2 — Game Rules**
The app detects game owners automatically. You can review and adjust things like minimum player counts, which days a game is allowed, or which venue it must be played at.

**Step 3 — Recommendations**
The app displays a timetable — rows are venues, columns are days. Each cell shows the game, the time, and how many players can make it. You also see "almost made it" games (high demand but couldn't fit) and games that couldn't be scheduled at all, with a plain-English reason for each.

**Step 4 — Insights**
Charts showing demand rankings, a player-vs-timeslot heatmap, coverage stats (which players got a session and which didn't), and a breakdown of rejected candidates.

---

## How It Works (Technical)

The scheduling engine is a three-layer pipeline.

### Layer 1 — Score Every Candidate (`engine/scorer.py`)

The app generates every possible combination of `(game, time slot, venue)` and applies **hard filters** first:

| Filter | Condition |
|--------|-----------|
| Allowed days | Game restricted to certain weekdays |
| Location lock | Game must run at a specific venue |
| Owner availability | Owner must be in the eligible player set |
| Minimum players | Eligible count must meet the game's floor |

Combinations that pass are scored using **six weighted components**:

| Component | Weight | What It Measures |
|-----------|--------|-----------------|
| Demand | 30% | Eligible players at this (slot, location) vs. the best possible |
| Coverage | 30% | Fraction of the entire group this session would serve |
| Availability | 15% | How busy this time slot is across all games |
| Popularity | 10% | Overall interest in the game, regardless of slot |
| Diversity | 10% | Niche games score higher — prevents popular titles from dominating |
| Location fit | 5% | Fraction of demand that this venue actually captures |

The final viability score is a float in `[0, 1]`. All candidates are sorted viable-first, descending by score.

### Layer 2 — Greedy Selection (`engine/selector.py`)

Starting from the highest-scored viable candidate, the algorithm iterates and checks three **hard constraints**:

1. **Table ceiling** — `(location, slot)` already has `max_tables_per_slot` sessions.
2. **Repeat limit** — this game already appears `max_repeats_per_week` times.
3. **Slot uniqueness** — this game is already running at this exact slot (only one physical copy).

If those pass, three **soft adjustments** are applied to the score:

- **Coverage bonus** (+0.3 × fraction of uncovered players this session reaches)
- **Conflict penalty** (−0.2 × Jaccard overlap with same-slot sessions)
- **Diversity multiplier** (÷ 2^n where n = times this game is already scheduled)

A session is added if the adjusted score is positive. Games that get blocked but would otherwise have been scheduled are tracked as **near-miss suggestions**.

**Smart overflow:** when a slot is full, a second table is allowed only if the game would otherwise go entirely unscheduled *and* the Jaccard player overlap with the existing session is below 0.5 — meaning the two tables serve genuinely different groups.

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

This installs four libraries: `streamlit` (the web UI), `plotly` (charts), `pandas` (data handling), and `pytest` (tests).

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
| Max game repeats per week | 2 | How many times the same game can appear in the schedule |
| Minimum players to run a game | 1 | Global floor; individual games can have higher requirements set in Step 2 |
| Max games at same time & place | 2 | How many tables can run simultaneously at one venue in one slot |

### Downloading sample files

In Step 1, click **Download sample CSVs** to get a zip of all four example files. Use them as templates for your own polls.

### Running Tests

```bash
pytest
```

The test suite covers the CSV loader, entity builder, scorer, selector, and explainer. All tests run without Streamlit and complete in under a second.

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
  scorer.py                  Layer 1 — hard filters + 6-component weighted scoring for every candidate
  selector.py                Layer 2 — greedy selection with overflow, soft adjustments, near-miss tracking
  explainer.py               Layer 3 — structured plain-English reasoning traces per session

models/
  entities.py                Dataclasses: Player, Game, Slot, Location, CandidateSession, SelectionResult
  config_model.py            SchedulerConfig (user-facing settings with validation)

ui/
  upload_panel.py            Step 1 — file upload, paste, example data, stat counters
  game_rules_panel.py        Step 2 — @st.fragment data editor with visual diff and per-game reset
  recommend_panel.py         Step 3 — day × location timetable, suggestions, non-viable section
  insights_panel.py          Step 4 — Plotly charts and analytics
  styles.py                  Dark-mode CSS, colour palette constants, HTML badge helpers

utils/
  names.py                   Name normalisation and fuzzy substring matching for owner detection

example_data/                Sample CSVs for local testing and the in-app "Use example data" toggle
tests/                       pytest unit tests — one file per engine/data module
```

### Key Design Decisions

**Pre-indexed overlap map.** Rather than filtering players per candidate at score time, `build_overlap_map` pre-indexes players by game, slot, and location into three dicts and then intersects them. This drops the inner loop from O(players × games × slots × locations) to O(games × slots × locations) with cheap set operations.

**`@st.fragment` on the rules editor.** The data editor in Step 2 triggers a Streamlit rerun on every cell change. Wrapping it in `@st.fragment` scopes reruns to just that component, preventing the page from scrolling to the top on every keystroke.

**Near-miss suggestions.** The selector tracks the best blocked candidate per unscheduled game. After selection completes, any game with zero sessions gets its best candidate surfaced as a "suggestion" with a human-readable reason — making the schedule explainable not just for what was chosen but for what was left out.

**Scoring weights.** All six weights are defined as module-level constants in `config.py` (`W_DEMAND`, `W_COVERAGE`, etc.). They are intentionally not exposed in the UI — the defaults were tuned against the example dataset, but they can be adjusted there for different group dynamics.

### Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | 1.55.0 | Web UI framework |
| `plotly` | 6.6.0 | Interactive charts in the Insights panel |
| `pandas` | 2.3.3 | CSV parsing and DataFrame operations |
| `pytest` | 9.0.2 | Unit testing |
