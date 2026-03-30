# Now Boarding Scheduler

A weekly board-game session planner for [Now Boarding — Board Game Café](https://www.nowboarding.co.in), Bengaluru.

Upload poll results from your gaming group, and the app builds an optimised weekly schedule — picking the right games, days, and venues automatically.

**Locations:**
[Now Boarding, HSR Layout](https://maps.app.goo.gl/x8mDruJ4M3BGVekBA) · [Now Boarding, Jayanagar](https://maps.app.goo.gl/5QBuavASgUroa1z79)

---

## How to Use the App

The app is a four-step wizard. You move through each step with Next / Back buttons.

### Step 1 — Upload Your Data

You need four CSV files (or you can paste the data directly):

| File | What It Contains |
|------|-----------------|
| **Heavy Games** | Which complex/long games (3+ hrs) each person wants to play |
| **Medium Games** | Which lighter/shorter games (1–3 hrs) each person wants to play |
| **Timings** | When each person is free (e.g. Tuesday 6 PM, Saturday 1 PM) |
| **Locations** | Where each person can go (e.g. Jayanagar, HSR Layout) |

Each file has a `Name` column with player names and a `✓` in the columns they voted for.

> **Tip:** Don't have your own data yet? Toggle **"Use example data"** in the sidebar to try it out with sample polls.

You can also tweak a few settings in the sidebar:

- **Max game repeats per week** — how many times the same game can appear (default: 2)
- **Minimum players to run a game** — the floor for a session to be viable (default: 1)
- **Max games at same time & place** — how many tables can run simultaneously at one venue (default: 2)

### Step 2 — Game Rules

The app auto-detects games and their owners from the poll data. This screen lets you fine-tune things before the schedule is generated:

- **Min Players** — set a per-game minimum (e.g. a game that needs at least 3)
- **Owner** — who owns the physical copy (they must be present for the session to happen)
- **Allowed Days** — restrict a game to certain days (uncheck days it shouldn't be played)
- **Location Lock** — force a game to a specific venue (e.g. the owner's neighbourhood)

### Step 3 — Recommendations

This is the main output: a **timetable grid** showing the best sessions for the week.

- Rows are venues, columns are days
- Each cell shows the game, time, and how many players can make it
- Below the timetable you'll see:
  - **Almost made it** — popular games that nearly got scheduled, with the reason they didn't
  - **Can't be scheduled** — games that failed hard constraints, grouped by reason

### Step 4 — Insights

Visual analytics to understand the data behind the schedule:

- **Game Demand Ranking** — which games are most wanted
- **Demand Heatmap** — a game-by-timeslot grid showing where demand is strongest
- **Player Coverage** — how many people got at least one session (and who didn't)
- **Location Split** — how player preferences are distributed across venues
- **Unviable Games** — a table of every game/slot/location that couldn't work, with the reason

---

## How the Algorithm Works

The scheduler uses a three-layer pipeline: **Score → Select → Explain**.

### Layer 1 — Score Every Possibility

The app looks at every possible combination of (game, time slot, venue) and asks two questions:

**Can this even happen?** It checks four hard rules:
1. Is this game allowed on this day? (Some games are restricted to weekends, for example.)
2. Is this the right venue? (If a game is locked to a specific location.)
3. Is the game owner free at this time and place? (No owner = no physical copy.)
4. Are enough players available? (Below the minimum = can't run.)

If any rule fails, that combination is rejected with a reason.

**How good is this option?** For combinations that pass, the app calculates a score based on six factors:

| Factor | What It Measures |
|--------|-----------------|
| **Demand** | How many interested players can actually make this session |
| **Coverage** | What fraction of the whole group this session would serve |
| **Diversity** | Niche games score higher — so the schedule isn't all the same popular titles |
| **Popularity** | A small boost for widely-loved games |
| **Availability** | Prefers time slots when more people are free |
| **Location fit** | How well this venue serves this game's fans |

These are combined into a single score between 0 and 1.

### Layer 2 — Build the Schedule (Greedy Selection)

Starting from the highest-scored option, the app tries to add sessions one by one:

1. **Is the table free?** Each venue + time slot has a limited number of tables.
2. **Has this game been picked too many times already?** Respects the weekly repeat limit.
3. **Is this game already running at this exact time elsewhere?** Only one physical copy exists.

If a session passes those checks, the app applies three soft adjustments:

- **Coverage bonus** — extra credit if this session includes players who don't have any session yet
- **Conflict penalty** — a deduction if this session fights over the same players as another session at the same time
- **Diminishing returns** — each time a game is picked again, its score is halved (so variety wins naturally)

If the adjusted score is still positive, the session is added to the schedule.

### Layer 3 — Explain Every Decision

For each selected session, the app generates plain-English reasoning:

- *"Food Chain Magnate has 8 interested players — highest demand this week"*
- *"5 of those 8 are free at Tuesday 6 PM and prefer HSR Layout"*
- *"Ranked #1. Covers 5 new players. Owner Grace is available."*
- *"Shares 3 players with Kanban EV"*

This makes the schedule transparent — you can always understand *why* a game was chosen or skipped.

---

## Project Structure

```
app.py                  Main Streamlit app (4-step wizard)
config.py               Scoring weights and constants
requirements.txt        Python dependencies

data/
  loader.py             CSV parsing and validation
  processor.py          Builds players, games, slots, locations, and derived indices
  validators.py         Cross-file consistency checks

engine/
  scorer.py             Layer 1 — scores every (game, slot, location) combination
  selector.py           Layer 2 — greedy schedule builder
  explainer.py          Layer 3 — human-readable reasoning

models/
  config_model.py       User-facing configuration (max repeats, min players, etc.)
  entities.py           Data classes: Player, Game, Slot, Location, CandidateSession

ui/
  upload_panel.py       Step 1 — file upload / paste / example data
  game_rules_panel.py   Step 2 — editable game rules table
  recommend_panel.py    Step 3 — timetable + suggestions + non-viable section
  insights_panel.py     Step 4 — charts and analytics
  styles.py             Dark-mode CSS and colour palette

utils/
  names.py              Name normalisation and fuzzy matching

example_data/           Sample CSV polls for quick testing
tests/                  Unit tests (pytest)
```

---

## Getting Started

### Prerequisites

- Python 3.11+

### Install & Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. Toggle **"Use example data"** in the sidebar to try it immediately.

### Run Tests

```bash
pytest
```

---

## CSV Format Reference

All four files follow the same pattern: a `Name` column followed by data columns, with `✓` marking a vote.

**Games CSV** (heavy or medium):
```
Name,Bitoku,Kanban EV (courtesy Grace),On Mars (courtesy Grace)
Victor,✓,✓,
Alice,,✓,✓
Grace,✓,✓,✓
```

Game names in parentheses like `(courtesy Grace)` are automatically detected as the game owner.

**Timings CSV:**
```
Name,Tuesday 6 PM,Wednesday 6 PM,Thursday 6 PM,Saturday 1 PM
Oscar,✓,✓,✓,
Alice,✓,✓,✓,
```

**Locations CSV:**
```
Name,Jayanagar,HSR Layout
Oscar,,✓
Paul,✓,
Alice,,✓
```