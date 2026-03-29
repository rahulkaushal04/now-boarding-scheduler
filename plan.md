# Now Boarding Scheduler — System Architecture Plan

**Repo:** `now-boarding-scheduler`
**App Title:** Now Boarding Scheduler
**Café:** Now Boarding Cafe (HSR Layout & Jayanagar)

---

## 1. Problem Statement

The café owner runs weekly board game sessions across two locations. Each week, players vote via WhatsApp polls on which games they want to play, when they're available, and which location they prefer. The results are exported as CSVs.

**Current manual workflow:**
1. Collect poll CSVs (games, timings, locations)
2. Manually eyeball demand, cross-reference availability, pick which games to run at which slot/location
3. Post the schedule to the group/website
4. Players claim seats first-come-first-serve

**What this system automates:** Step 2 — the intelligence layer. Given poll data, the system recommends the best (game, time slot, location) combinations ranked by demand viability. The owner reviews, accepts/rejects, and publishes. Seat assignment remains FCFS after publishing.

**This is a scoring and ranking problem, not a constraint optimization problem.** The search space is tiny (~N games × T time slots × L locations ≈ a few hundred candidates), making brute-force scoring of every candidate trivially fast.

**All dimensions are dynamic.** The number of players, games, time slots, and locations changes every week based on poll participation. Nothing is hardcoded. There is **no database** — each run is a fresh CSV upload → recommendation → done.

---

## 2. Data Model

### 2.1 Stateless Architecture

```
Upload CSVs → Parse & Index → Owner adds game rules → Score all candidates → Rank → Owner picks → Export
```

Nothing persists between runs. No database. `st.session_state` for within-session state only.

### 2.2 Canonical Entities

```
Player
├── id: str (normalised name)
├── heavy_prefs: Set[GameId]
├── medium_prefs: Set[GameId]
├── all_prefs: Set[GameId]                # union of above
├── location_prefs: Set[LocationId]
└── time_availability: Set[SlotId]

Game
├── id: str (normalised name)
├── weight_class: "heavy" | "medium"
├── min_players: int                      # from metadata CSV
├── max_players: int                      # from metadata CSV
├── owner: Optional[PlayerId]             # who owns the physical copy (UI-editable)
├── allowed_days: Optional[Set[str]]      # day restrictions (UI-editable, e.g. {"Friday","Saturday","Sunday"})
└── location_lock: Optional[LocationId]   # location restriction (UI-editable)

Slot
├── id: str
├── day: str
└── time: str

Location
├── id: str

CandidateSession (the unit being scored)
├── game: GameId
├── slot: SlotId
├── location: LocationId
├── eligible_players: Set[PlayerId]
├── eligible_count: int
├── viability_score: float
├── score_breakdown: Dict[str, float]
├── viable: bool
├── rejection_reason: Optional[str]       # why it's non-viable (for UI display)
└── reasoning: Optional[SessionReasoning]

SessionReasoning
├── demand_reason: str
├── overlap_reason: str
├── selection_reason: str
├── conflict_note: Optional[str]
└── score_breakdown: Dict[str, float]
```

### 2.3 Game Constraints (UI-Editable)

These are per-game rules the owner sets through the UI after uploading CSVs. They act as hard filters on candidate generation.

| Constraint | Example | Effect |
|---|---|---|
| **Game owner** | "Kanban EV" → owner is "Kiran (BG)" | Session is only viable if Kiran is in the eligible set. Without him, the physical copy isn't available. |
| **Day restriction** | "Food Chain Magnate" → only Fri / Sat / Sun | Candidates at non-allowed days are auto-rejected. |
| **Location lock** | "Bitoku" → only HSR Layout | Candidates at other locations are auto-rejected. |

The system pre-populates owner from the game name pattern `"Game Name (courtesy PlayerName)"` found in the CSV headers. The owner can edit, add, or remove any of these via the UI.

### 2.4 Derived Indices (Built at Runtime)

| Structure | Type | Purpose |
|---|---|---|
| `demand_matrix` | `Dict[GameId, Set[PlayerId]]` | Who wants each game |
| `availability_index` | `Dict[SlotId, Set[PlayerId]]` | Who is free at each time |
| `location_roster` | `Dict[LocationId, Set[PlayerId]]` | Who prefers each location |
| `overlap_map` | `Dict[(GameId, SlotId, LocationId), Set[PlayerId]]` | **Core structure.** 3-way set intersection: want game ∩ free at time ∩ prefer location. |
| `conflict_matrix` | `Dict[(GameId, GameId), int]` | Players who want BOTH games — for demand-splitting avoidance |

---

## 3. Algorithm: Demand-Overlap Scoring + Greedy Selection

### 3.1 Why This Approach

~240 candidate sessions at café scale. Brute-force scoring is sub-millisecond. No solver needed.

| Algorithm | Fit | Explainability |
|---|---|---|
| **Weighted demand-overlap scoring** | ★★★★★ | Perfect — score breakdown visible |
| **Greedy selection** | ★★★★★ | Transparent — selection order clear |
| CSP / ILP / Genetic / Annealing | ★★–★★★ | Poor to moderate — overkill at this scale |

### 3.2 Layer 1 — Score Every Candidate

For each (game `g`, time slot `t`, location `l`) triple:

```
Step 1: Apply hard filters (game constraints from UI)
    if g.allowed_days is set and slot.day ∉ g.allowed_days → reject
    if g.location_lock is set and l ≠ g.location_lock → reject
    if g.owner is set and g.owner ∉ overlap_map[(g,t,l)] → reject

Step 2: Compute eligible player set
    eligible = overlap_map[(g, t, l)]
    if |eligible| < g.min_players → reject

Step 3: Compute composite viability score
    viability(g, t, l) =
        0.40 × normalise(overlap_count)               # demand: how many can attend
      + 0.10 × normalise(total_demand(g))              # popularity: overall game interest
      + 0.05 × normalise(slot_density(t))              # availability: prefer busier slots
      + 0.05 × location_alignment(g, t, l)             # location: demand fit
      + 0.20 × diversity_bonus(g)                      # diversity: reward unique games
      + 0.20 × coverage_potential(g, t, l)             # coverage: new players served

Step 4: Record score_breakdown and rejection_reason (if rejected)
```

**Scoring weights are internal (not UI-exposed).** The owner doesn't need to tune algorithm weights — they control outcomes through concrete, understandable parameters (game rules, session count, table limits). Weights are baked into the engine at sensible defaults:

| Component | Weight | What It Does |
|---|---|---|
| Demand | 0.40 | Eligible player overlap count — the primary signal |
| Diversity | 0.20 | Reward unique games, penalise repeats |
| Coverage | 0.20 | Reward sessions that serve players not yet covered |
| Popularity | 0.10 | Overall game interest across all slots |
| Availability | 0.05 | Prefer time slots when more players are around |
| Location | 0.05 | How well the location matches demand |

### 3.3 Layer 2 — Greedy Session Selection

```
Algorithm: SELECT_SESSIONS(ranked_candidates, config, conflict_matrix)

1.  Sort viable candidates by viability_score descending

2.  Track: occupied[location] → Set[slot], covered_players, game_counts

3.  For each candidate:
      Skip if location+slot at table capacity
      Skip if game already at max_repeats_per_week

      Compute adjusted_score:
        + coverage_bonus (new players / remaining uncovered)
        - conflict_penalty (shared players with session at same time)

      Accept → update tracking

4.  Stop at target_sessions or candidates exhausted

5.  Return selected, sorted by time slot
```

---

## 4. Constraint System

### 4.1 Hard Constraints (Reject Candidate if Violated)

| ID | Constraint | Source |
|---|---|---|
| H1 | `eligible_count >= game.min_players` | Metadata CSV |
| H2 | `tables_at(location, slot) < max_tables_per_slot` | UI config |
| H3 | `game_count < max_repeats_per_week` | UI config |
| H4 | If `game.owner` set → `owner ∈ eligible_players` | UI game rules |
| H5 | If `game.allowed_days` set → `slot.day ∈ allowed_days` | UI game rules |
| H6 | If `game.location_lock` set → `location == location_lock` | UI game rules |

### 4.2 Soft Constraints (Baked into Scoring Weights)

| Goal | How Applied |
|---|---|
| Maximise player coverage | Coverage component in scoring + coverage bonus in selection |
| Game diversity | Diminishing returns multiplier (1.0 → 0.5 → 0.25) |
| Avoid demand-splitting | Conflict penalty in greedy selection |
| Location spread | Location alignment component |
| Weight class balance | Implicit via diversity — heavy and medium compete equally |

### 4.3 Configurable Parameters (UI-Exposed)

Only parameters the owner actually needs to think about. No algorithm weights.

| Parameter | Type | Default | UI Widget |
|---|---|---|---|
| Target sessions per week | int | 4 | Number input (1–10) |
| Max tables per slot per location | int | 1 | Number input (1–3) |
| Max repeats of a game per week | int | 1 | Number input (1–3) |

### 4.4 Game-Specific Rules (UI-Exposed Per Game)

After CSVs are uploaded and games are discovered, the owner sees a **Game Rules Editor** — a table listing every discovered game with editable columns:

| Column | Type | Default | Example |
|---|---|---|---|
| Game Name | read-only | from CSV | "Kanban EV" |
| Weight Class | read-only | from CSV | Heavy |
| Min Players | number | from metadata | 3 |
| Max Players | number | from metadata | 4 |
| Owner | dropdown (player list + "None") | auto-detected from courtesy pattern | "Kiran (BG)" |
| Allowed Days | multi-select (from discovered days) | All days | Fri, Sat, Sun |
| Location | dropdown (discovered locations + "Any") | Any | "HSR Layout" |

**Auto-detection:** The system scans game names for patterns like `"Kanban EV (courtesy Kiran)"` and pre-fills the Owner field with the matched player. The owner can override any auto-detected value.

**This is the key UX insight:** instead of abstract weight sliders, the owner expresses constraints in language they already think in — "Kiran has Kanban EV", "FCM only works on weekends", "Bitoku only at HSR."

---

## 5. Explainability Layer

Every recommended session carries a reasoning trace:

```python
@dataclass
class SessionReasoning:
    demand_reason: str
    # "Kanban EV has 11 interested players — highest demand this week."

    overlap_reason: str
    # "8 of those 11 are free Tuesday 6 PM and prefer HSR Layout."

    selection_reason: str
    # "Ranked #1. Covers 8 new players. Owner Kiran is available."

    conflict_note: str | None
    # "Shares 4 players with Food Chain Magnate — avoided same slot."

    score_breakdown: Dict[str, float]
```

For **rejected** candidates, `rejection_reason` explains why:
- "Only 2 eligible players — below minimum of 3"
- "Owner Kiran (BG) is not available at this time/location"
- "Food Chain Magnate restricted to Fri/Sat/Sun — Tuesday rejected"
- "HSR Layout already at table capacity for this slot"

---

## 6. Output: What the Owner Gets

### 6.1 Recommended Schedule
Ranked session cards with game, slot, location, eligible count, score, reasoning, accept/skip.

### 6.2 Owner Actions
- **Accept** → moves to final schedule
- **Skip** → next recommendation surfaces
- **Export** → CSV download + WhatsApp-formatted text

### 6.3 After Publishing
FCFS seat claiming — outside this system's scope.

---

## 7. Insights & Analytics

| Insight | What It Shows |
|---|---|
| **Demand Heatmap** | Game × time slot grid, cell intensity = eligible count per location |
| **Game Demand Ranking** | Bar chart of interested players per game |
| **Conflict Matrix** | Shared-player counts between game pairs |
| **Player Coverage** | Who has ≥ 1 session available, who's unserved and why |
| **Location Split** | HSR vs Jayanagar demand comparison |
| **Unviable Games** | Games that failed constraints, with specific reasons |
| **Time Slot Density** | Available players per slot |

---

## 8. UI/UX Design (TOP PRIORITY)

> **Dark mode only. The interface must feel premium, modern, and branded for Now Boarding Cafe.**

### 8.1 Dark Mode Colour Palette

| Role | Colour | Hex | Usage |
|---|---|---|---|
| Background | Rich Black | `#0E1117` | Page background (Streamlit dark default) |
| Surface | Dark Charcoal | `#1B1F27` | Cards, panels, modals |
| Surface Raised | Slate | `#262B36` | Hover states, active cards, expanded sections |
| Primary | Electric Teal | `#00D4AA` | Primary buttons, active states, score bars, links |
| Primary Muted | Faded Teal | `#00A88A` | Secondary buttons, borders on active elements |
| Accent | Warm Gold | `#FFB830` | Badges, highlights, demand indicators, Medium game tags |
| Alert | Soft Red | `#FF6B6B` | Errors, non-viable indicators, conflict warnings |
| Warning | Amber | `#FFA726` | Warnings, partial issues |
| Success | Mint Green | `#69F0AE` | Accepted sessions, viable indicators, checkmarks |
| Text Primary | Off-White | `#E6E6E6` | Body text |
| Text Secondary | Cool Grey | `#9CA3AF` | Labels, captions, secondary info |
| Text Muted | Dark Grey | `#6B7280` | Disabled states, subtle annotations |
| Border | Subtle Grey | `#2D333B` | Card borders, dividers |
| Heavy Tag | Electric Teal | `#00D4AA` | Left-border accent on Heavy game cards |
| Medium Tag | Warm Gold | `#FFB830` | Left-border accent on Medium game cards |

**Typography:** `'Inter', sans-serif` for all text. `'JetBrains Mono', monospace` for debug/code sections.

**Design Principles:**
- High contrast text on dark backgrounds for readability
- Cards with subtle borders (`#2D333B`) and gentle elevation on hover
- Colour is used sparingly for meaning — teal = action/positive, gold = attention, red = problem
- No gradients, no glows, no neon — clean and matte

### 8.2 App Flow — Step-by-Step Wizard

```
┌───────────────────────────────────────────────────────────────────────────┐
│  �� Now Boarding Scheduler                                                 │
├───────────────────────────────────────────────────────────────────────────┤
│  ① Upload  →  ② Game Rules  →  ③ Recommendations  →  ④ Insights          │
└───────────────────────────────────────────────────────────────────────────┘
```

**Step 1 — Upload:**
- 5 drag-and-drop zones with labels
- Each shows: file name, row/column count, green checkmark or red warning
- Cross-file validation runs automatically
- Summary card: "Found N players · G games · T time slots · L locations"
- Also shows: Target sessions (number input), Max tables/slot (number input), Max repeats (number input)

**Step 2 — Game Rules (NEW):**
- **Editable table** listing every discovered game
- Columns: Game Name (read-only) | Min | Max | Owner (dropdown) | Allowed Days (multi-select) | Location (dropdown)
- Pre-populated from metadata CSV + auto-detected courtesy owners
- Owner dropdown lists all discovered player names + "None"
- Days multi-select lists all discovered days (e.g., Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday) — default: all selected
- Location dropdown lists discovered locations + "Any" — default: "Any"
- This replaces the abstract config panel from previous design — real constraints, not weights

**Step 3 — Recommendations (main screen):**

```
┌─────────────────── Your Schedule (2 of 4) ──────────────────────┐
│  ✅ Kanban EV · Tue 6 PM · HSR · 8 players                      │
│  ✅ Scythe · Thu 6 PM · Jayanagar · 5 players                   │
│  Coverage: 13 of 28 players                                      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────── Recommendation #3 ──────────────────────────┐
│  �� Food Chain Magnate                                [Heavy]    │
│  �� Friday 6 PM  ·  �� HSR Layout                               │
│  �� 6 eligible (of 8 interested)                                 │
│  ████████████░░░░  74%                                           │
│  ▸ Why this recommendation?                                      │
│  [✅ Accept]  [⏭ Skip]                                           │
└─────────────────────────────────────────────────────────────────┘
```

- Dark surface cards with teal left-border (Heavy) or gold left-border (Medium)
- Score bar: teal fill on dark background
- Expandable reasoning section
- Live coverage counter updates on accept
- Rejected/non-viable candidates shown below in collapsed "Not viable" section with reasons

**Step 4 — Insights:**
- All charts use dark-mode-friendly colours (teal, gold, red on dark backgrounds)
- Plotly dark template (`plotly_dark`)
- Export buttons: CSV download + WhatsApp copy-paste text

### 8.3 Micro-interactions & Polish

| Element | Detail |
|---|---|
| **Loading** | "Crunching the numbers..." spinner during scoring |
| **Empty states** | "Upload your poll CSVs to get started ��" on dark surface card |
| **Error states** | Soft red bordered cards with clear fix action |
| **Score bars** | Teal fill on dark track, percentage label |
| **Card hover** | Background shifts from `#1B1F27` to `#262B36` |
| **Accepted badge** | Mint green checkmark + "Accepted" pill |
| **Tooltips** | On all config inputs explaining what they do |
| **Step indicator** | Current step in teal, completed steps with checkmark, future steps in grey |

### 8.4 CSS & Theming

Force dark mode via Streamlit config + custom CSS:

```python
# In .streamlit/config.toml:
[theme]
base = "dark"
primaryColor = "#00D4AA"
backgroundColor = "#0E1117"
secondaryBackgroundColor = "#1B1F27"
textColor = "#E6E6E6"

# Additional overrides in styles.py via st.markdown:
def inject_custom_css():
    st.markdown("""
    <style>
    .session-card {
        background: #1B1F27;
        border: 1px solid #2D333B;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.75rem;
    }
    .session-card:hover {
        background: #262B36;
        transition: background 0.2s ease;
    }
    .tag-heavy { border-left: 4px solid #00D4AA; }
    .tag-medium { border-left: 4px solid #FFB830; }
    .score-bar {
        background: #262B36;
        border-radius: 6px;
        overflow: hidden;
    }
    .score-fill {
        background: #00D4AA;
        height: 8px;
        border-radius: 6px;
    }
    .badge-accepted {
        background: rgba(105, 240, 174, 0.15);
        color: #69F0AE;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
    }
    .badge-rejected {
        background: rgba(255, 107, 107, 0.15);
        color: #FF6B6B;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85em;
    }
    </style>
    """, unsafe_allow_html=True)
```

---

## 9. Edge Cases

| Case | Handling |
|---|---|
| Player in game CSV but not in timing/place CSV | Excluded from overlaps; flagged as warning |
| Player name variations | Normalisation: strip, lowercase, collapse whitespace |
| Game with 0 interested players | Excluded, listed in "No demand" insight |
| Game below min_players at every slot | Listed in "Unviable" with reason |
| Courtesy owner unavailable everywhere | Game flagged: "Owner {name} has no overlapping availability" |
| Owner field changed via UI | Overrides auto-detection; triggers re-scoring |
| Day restriction eliminates all viable slots | Game flagged: "No viable slots within allowed days" |
| Location lock + no players at that location | Game flagged: "No players prefer {location} for this game" |
| Different dimensions each week | All discovered from CSVs |
| Only one location has voters | Single-location mode |
| Only one time slot has voters | Schedules up to max_tables at that slot |
| Game in poll but missing from metadata | Blocking warning with game name |
| CSV "Total" rows/columns | Stripped during loading |
| High demand (15+ for one game) | Multiple sessions if max_repeats allows |
| Low participation (<5 total) | Works; warns "Limited participation" |

---

## 10. Assumptions

1. **Recommendation engine, not seat assigner.** FCFS after publishing.
2. **Fully stateless.** No database. Fresh CSVs every week.
3. **All dimensions dynamic.** Discovered from CSVs.
4. **One session = one game at one table.**
5. **Time slots equivalent in duration.**
6. **Game metadata must cover all polled games.**
7. **Eligible ≠ confirmed.** Upper bound on attendance.
8. **Scoring weights are internal.** Owner controls outcomes via game rules and session config, not abstract algorithm tuning.

---

## 11. Trade-offs

| Decision | Trade-off |
|---|---|
| **Scoring + greedy over solvers** | Near-optimal at ~240 candidates. Zero dependencies. |
| **Game rules UI over weight sliders** | Owner thinks in "Kiran owns Kanban" not "set w_demand to 0.4". Less flexible but far more intuitive. |
| **Internal weights** | Can't fine-tune algorithm, but sensible defaults work for this scale. Avoids confusing the owner. |
| **Recommendation over auto-assignment** | Requires human review. Allows context the system doesn't have. |
| **FCFS over algorithmic seats** | Simple, familiar. Late responders may miss out. |
| **No database** | Zero setup. No cross-week memory. |
| **Dark mode only** | Cleaner look, less testing. Users who prefer light mode can't switch. |

---

## 12. Data Pipeline Summary

```
CSV Upload (variable dimensions)
    │
    ▼
┌───────────────────────────┐
│  Parse & Validate          │  → N players, G games, T slots, L locations
│  (data/loader.py)          │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Build Indices             │  → overlap_map, demand_matrix, conflict_matrix
│  (data/processor.py)       │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Owner Sets Game Rules     │  → owner, allowed_days, location_lock per game
│  (ui/game_rules_panel.py)  │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Score All Candidates      │  → viability + breakdown for each (g, t, l)
│  (engine/scorer.py)        │  → apply game rules as hard filters
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Greedy Selection          │  → top N non-conflicting sessions
│  (engine/selector.py)      │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Generate Reasoning        │  → per-session explanations
│  (engine/explainer.py)     │
└────────┬──────────────────┘
         │
         ▼
┌───────────────────────────┐
│  Present to Owner          │  → ranked cards, accept/skip, export
│  (app.py + ui/)            │
└───────────────────────────┘
```