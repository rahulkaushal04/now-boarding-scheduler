"""Tests for engine/selector.py — session selection and display post-processing."""

from __future__ import annotations

from models.entities import CandidateSession, Game
from models.config_model import SchedulerConfig
from engine.selector import select_sessions, _slot_sort_key


def _candidate(
    game: str,
    slot: str,
    location: str,
    players: list[str],
    score: float = 0.5,
) -> CandidateSession:
    """Create a minimal viable CandidateSession for testing."""
    return CandidateSession(
        game=game,
        slot=slot,
        location=location,
        eligible_players=set(players),
        eligible_count=len(players),
        viability_score=score,
        viable=True,
    )


def _games(*ids: str, min_players: int = 1, owner: str | None = None) -> dict[str, Game]:
    """Build a default games dict (medium weight class, no owner) for the given ids."""
    return {
        gid: Game(id=gid, weight_class="medium", min_players=min_players, owner=owner)
        for gid in ids
    }


def _demand_from(candidates: list[CandidateSession]) -> dict[str, set[str]]:
    """Default demand matrix: each game's demand equals the union of its candidates'
    eligible players (reasonable default when a test doesn't care about Tier 3)."""
    demand: dict[str, set[str]] = {}
    for c in candidates:
        demand.setdefault(c.game, set()).update(c.eligible_players)
    return demand


def _run(
    candidates: list[CandidateSession],
    config: SchedulerConfig | None = None,
    games: dict[str, Game] | None = None,
    demand: dict[str, set[str]] | None = None,
):
    config = config or SchedulerConfig()
    games = games if games is not None else _games(*{c.game for c in candidates})
    demand = demand if demand is not None else _demand_from(candidates)
    return select_sessions(candidates, config, games, demand)


class TestSlotSortKey:
    def test_chronological_ordering(self):
        """Weekdays sort Mon→Sun regardless of alphabetical order."""
        slots = [
            "Friday, 6 PM",
            "Saturday, 1 PM",
            "Sunday, 1 PM",
            "Thursday, 6 PM",
            "Tuesday, 6 PM",
            "Wednesday, 6 PM",
        ]
        sorted_slots = sorted(slots, key=_slot_sort_key)
        assert sorted_slots == [
            "Tuesday, 6 PM",
            "Wednesday, 6 PM",
            "Thursday, 6 PM",
            "Friday, 6 PM",
            "Saturday, 1 PM",
            "Sunday, 1 PM",
        ]

    def test_unknown_day_sorts_last(self):
        """Unrecognised weekday names sort after all known days."""
        assert _slot_sort_key("Someday, 6 PM")[0] == 99
        assert _slot_sort_key("Tuesday, 6 PM")[0] < 99

    def test_same_day_secondary_sort_by_slot_id(self):
        """Two sessions on the same day break ties by full slot string."""
        a = _slot_sort_key("Tuesday, 6 PM")
        b = _slot_sort_key("Tuesday, 8 PM")
        assert a < b


class TestSelectedListChronologicalOrder:
    def test_selected_sorted_chronologically(self):
        """result.selected is returned in Mon→Sun day order, not alphabetical."""
        c_fri = _candidate("G1", "Friday, 6 PM", "L1", ["A"])
        c_tue = _candidate("G2", "Tuesday, 6 PM", "L1", ["B"])
        c_sun = _candidate("G3", "Sunday, 1 PM", "L1", ["C"])
        result = _run([c_fri, c_tue, c_sun])
        slots = [s.slot for s in result.selected]
        assert slots == ["Tuesday, 6 PM", "Friday, 6 PM", "Sunday, 1 PM"]


class TestTableCapacity:
    def test_disjoint_games_both_open_a_second_table(self):
        """Two games with disjoint player sets both run — opening the second
        table strictly increases coverage, so it's worth it."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S1", "L1", ["C", "D"])
        result = _run([c1, c2])
        assert len(result.selected) == 2
        assert result.selected[1].is_overflow is True

    def test_overlapping_audiences_both_run_and_split_the_group(self):
        """Two games sharing most of their audience are no longer blocked by
        an arbitrary similarity threshold: the optimizer runs both and
        splits the shared players between them (nobody can attend both, since
        it's the same slot), because doing so strictly increases coverage.
        """
        c1 = _candidate("G1", "S1", "L1", ["A", "B", "C"])
        c2 = _candidate("G2", "S1", "L1", ["A", "B", "D"])
        result = _run([c1, c2])
        assert len(result.selected) == 2
        # No player is double-counted: exclusivity per slot is respected.
        assigned_a = [c for c in result.selected if "A" in c.assigned_players]
        assert len(assigned_a) <= 1
        covered = {p for c in result.selected for p in c.assigned_players}
        assert covered == {"A", "B", "C", "D"}

    def test_hard_ceiling_blocks_third_table(self):
        """max_tables_per_slot=2 blocks a third game at the same slot."""
        c1 = _candidate("G1", "S1", "L1", ["A"])
        c2 = _candidate("G2", "S1", "L1", ["B"])
        c3 = _candidate("G3", "S1", "L1", ["C"])
        config = SchedulerConfig(max_tables_per_slot=2)
        result = _run([c1, c2, c3], config=config)
        assert len(result.selected) == 2

    def test_second_table_allowed_for_a_game_scheduled_elsewhere_when_it_adds_coverage(
        self,
    ):
        """A second table is allowed for a game already scheduled elsewhere
        this week, as long as it covers players nobody else reaches.
        """
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S2", "L1", ["C", "D"])
        c3 = _candidate("G2", "S1", "L1", ["E", "F"])
        result = _run([c1, c2, c3])
        games_at_s1 = [s for s in result.selected if s.slot == "S1"]
        assert len(games_at_s1) == 2
        covered = {p for s in result.selected for p in s.assigned_players}
        assert covered == {"A", "B", "C", "D", "E", "F"}

    def test_different_locations_ok(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S1", "L2", ["C", "D"])
        result = _run([c1, c2])
        assert len(result.selected) == 2

    def test_per_location_table_capacity_override(self):
        """tables_per_location overrides max_tables_per_slot for a specific venue."""
        c1 = _candidate("G1", "S1", "L1", ["A"])
        c2 = _candidate("G2", "S1", "L1", ["B"])
        c3 = _candidate("G3", "S1", "L1", ["C"])
        config = SchedulerConfig(max_tables_per_slot=2, tables_per_location={"L1": 1})
        result = _run([c1, c2, c3], config=config)
        assert len(result.selected) == 1


class TestSelectsAllQualityCandidates:
    def test_selects_all_disjoint_games(self):
        candidates = [
            _candidate(f"G{i}", f"S{i}", "L1", [f"P{i}"]) for i in range(5)
        ]
        result = _run(candidates)
        assert len(result.selected) == 5

    def test_repeat_visits_at_different_slots_both_count_toward_revenue(self):
        """The same two players eligible for the same game-ish setup at two
        different slots: both sessions get scheduled because a repeat visit
        by an already-served player still adds real revenue (attendance),
        and nothing forces the schedule to stay minimal beyond parsimony
        among *tied* solutions.
        """
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S2", "L1", ["A", "B"])
        result = _run([c1, c2])
        assert len(result.selected) == 2


class TestCoverageBonus:
    def test_prefers_new_players(self):
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S2", "L1", ["A", "B"])
        c3 = _candidate("G3", "S3", "L1", ["C", "D"])
        result = _run([c1, c2, c3])
        games = {s.game for s in result.selected}
        assert "G1" in games
        assert "G3" in games


class TestSameSlotDifferentLocation:
    def test_overlap_across_locations_still_all_run(self):
        """Same slot, different locations: the café can run both tables
        simultaneously even though some players are eligible for both —
        those players just get assigned to one location, not both."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B", "C"])
        c2 = _candidate("G2", "S1", "L2", ["A", "B", "D"])
        c3 = _candidate("G3", "S2", "L1", ["E", "F"])
        result = _run([c1, c2, c3])
        assert len(result.selected) == 3
        covered = {p for c in result.selected for p in c.assigned_players}
        assert covered == {"A", "B", "C", "D", "E", "F"}

    def test_player_not_assigned_to_two_locations_at_once(self):
        """A player eligible for two simultaneous sessions at different
        locations can only actually be assigned to one of them."""
        c1 = _candidate("G1", "S1", "L1", ["A"])
        c2 = _candidate("G2", "S1", "L2", ["A"])
        result = _run([c1, c2])
        assigned_to_both = c1.assigned_players & c2.assigned_players
        assert assigned_to_both == set()


class TestDayLocationExclusivity:
    def test_same_game_cannot_switch_location_same_day_different_slots(self):
        """A game can't run at HSR at one slot and Jayanagar at another slot
        on the *same day* — the physical copy can't move cafés mid-day."""
        c_hsr = _candidate("G1", "Tuesday, 6 PM", "HSR", ["A"])
        c_jay = _candidate("G1", "Tuesday, 8 PM", "Jayanagar", ["B"])
        result = _run([c_hsr, c_jay])
        locations_used = {c.location for c in result.selected}
        assert len(locations_used) <= 1

    def test_same_game_can_switch_location_on_a_different_day(self):
        """The same game *can* run at a different café on a different day."""
        c_hsr = _candidate("G1", "Tuesday, 6 PM", "HSR", ["A"])
        c_jay = _candidate("G1", "Wednesday, 6 PM", "Jayanagar", ["B"])
        result = _run([c_hsr, c_jay])
        assert len(result.selected) == 2


class TestMinPlayersEnforcedOnRealAssignment:
    def test_session_not_run_if_real_assignment_would_fall_short(self):
        """Two games with min_players=2 share their only two eligible fans at
        the same slot. Running both would force a 1-1 split, which fails
        the min_players floor for a session — so only one may run."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S1", "L1", ["A", "B"])
        games = _games("G1", "G2", min_players=2)
        result = _run([c1, c2], games=games)
        assert len(result.selected) == 1
        assert result.selected[0].assigned_count >= 2


class TestOwnerMustAttend:
    def test_owner_assigned_to_every_session_of_their_game(self):
        c1 = _candidate("G1", "S1", "L1", ["Owner", "A", "B"])
        games = {"G1": Game(id="G1", weight_class="medium", min_players=1, owner="Owner")}
        result = _run([c1], games=games)
        assert len(result.selected) == 1
        assert "Owner" in result.selected[0].assigned_players


class TestSuggestions:
    def test_suggestion_when_table_capacity_forces_a_choice(self):
        """With only one table available, the optimizer must pick one of two
        equally-good games — the other becomes a suggestion."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S1", "L1", ["A", "B"])
        config = SchedulerConfig(max_tables_per_slot=1)
        result = _run([c1, c2], config=config)
        assert len(result.selected) == 1
        assert len(result.suggestions) == 1
        assert result.suggestions[0].suggestion_reason is not None
        assert "full" in result.suggestions[0].suggestion_reason.lower()

    def test_no_suggestion_when_game_is_scheduled(self):
        """Games that made the schedule should not appear as suggestions."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S2", "L1", ["C", "D"])
        result = _run([c1, c2])
        assert len(result.selected) == 2
        assert len(result.suggestions) == 0

    def test_game_scheduled_via_a_better_slot_is_not_a_suggestion(self):
        """A game with a redundant, zero-value duplicate candidate at a busy
        slot still counts as scheduled via its other, useful candidate."""
        c1 = _candidate("G1", "S1", "L1", ["A", "B"])
        c2 = _candidate("G2", "S1", "L1", ["A", "B"])  # redundant duplicate of c1's slot
        c3 = _candidate("G2", "S2", "L1", ["A", "B"])  # G2's real opportunity
        result = _run([c1, c2, c3])
        g2_sessions = [s for s in result.selected if s.game == "G2"]
        assert len(g2_sessions) == 1
        assert len(result.suggestions) == 0
