"""Domain entities for the scheduler: players, games, slots, and sessions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Player:
    """Represent a single participant's preferences and availability.

    Aggregates a player's game preferences by weight class along with
    time and location constraints extracted from poll CSV inputs.

    Attributes:
        id: Unique player identifier (name as read from the CSV).
        heavy_prefs: Games in the heavy category the player voted for.
        medium_prefs: Games in the medium category the player voted for.
        all_prefs: Union of heavy_prefs and medium_prefs for fast lookup.
        location_prefs: Venues the player is willing to play at.
        time_availability: Time-slot identifiers the player is available for.
    """

    id: str
    heavy_prefs: set[str] = field(default_factory=set)
    medium_prefs: set[str] = field(default_factory=set)
    all_prefs: set[str] = field(default_factory=set)
    location_prefs: set[str] = field(default_factory=set)
    time_availability: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the player to a JSON-friendly dict.

        Sorts all set fields for deterministic output.

        Returns:
            dict[str, Any]: Player data with sorted lists for set fields.

        Example:
            >>> p = Player(id="Alice", heavy_prefs={"Scythe"})
            >>> p.to_dict()["id"]
            'Alice'
        """
        return {
            "id": self.id,
            "heavy_prefs": sorted(self.heavy_prefs),
            "medium_prefs": sorted(self.medium_prefs),
            "all_prefs": sorted(self.all_prefs),
            "location_prefs": sorted(self.location_prefs),
            "time_availability": sorted(self.time_availability),
        }


@dataclass(slots=True)
class Game:
    """Represent a schedulable board game with optional scheduling constraints.

    Attributes:
        id: Canonical game name used as the primary key.
        weight_class: Complexity tier — ``"heavy"`` or ``"medium"``.
        min_players: Minimum eligible players required to run the game.
        owner: Player who owns the game and must be present, or ``None``.
        allowed_days: Days the game may run; ``None`` means no restriction.
        location_lock: Venue the game must be played at; ``None`` means any.
    """

    id: str
    weight_class: str  # "heavy" | "medium"
    min_players: int = 1
    owner: str | None = None
    allowed_days: set[str] | None = None
    location_lock: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the game to a JSON-friendly dict.

        Returns:
            dict[str, Any]: Game data with ``allowed_days`` as a sorted list.

        Example:
            >>> g = Game(id="Scythe", weight_class="heavy", min_players=2)
            >>> g.to_dict()["weight_class"]
            'heavy'
        """
        return {
            "id": self.id,
            "weight_class": self.weight_class,
            "min_players": self.min_players,
            "owner": self.owner,
            "allowed_days": sorted(self.allowed_days) if self.allowed_days else None,
            "location_lock": self.location_lock,
        }


@dataclass(slots=True)
class Slot:
    """Represent a discrete scheduling time slot.

    Attributes:
        id: Full slot identifier as it appears in the timings CSV
            (e.g. ``"Tuesday, 6 PM"``).
        day: Day of the week extracted from the slot id.
        time: Time portion extracted from the slot id.
    """

    id: str
    day: str
    time: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the slot to a JSON-friendly dict.

        Returns:
            dict[str, str]: Mapping of ``id``, ``day``, and ``time``.

        Example:
            >>> Slot(id="Tuesday, 6 PM", day="Tuesday", time="6 PM").to_dict()
            {'id': 'Tuesday, 6 PM', 'day': 'Tuesday', 'time': '6 PM'}
        """
        return {"id": self.id, "day": self.day, "time": self.time}


@dataclass(slots=True)
class Location:
    """Represent a physical venue where games can be played.

    Attributes:
        id: Venue name as it appears in the location poll CSV.
    """

    id: str

    def to_dict(self) -> dict[str, str]:
        """Serialize the location to a JSON-friendly dict.

        Returns:
            dict[str, str]: Single-key mapping of ``id`` to the venue name.

        Example:
            >>> Location(id="HSR Layout").to_dict()
            {'id': 'HSR Layout'}
        """
        return {"id": self.id}


@dataclass(slots=True)
class SessionReasoning:
    """Human-readable reasoning traces for a scheduled session.

    Attributes:
        demand_reason: Explains why the game has demand (player count context).
        overlap_reason: Explains how many players are free at the chosen slot.
        selection_reason: Explains rank, new players covered, and owner presence.
        conflict_note: Describes shared players with other selected sessions,
            or ``None`` when there are no conflicts.
        score_breakdown: Component scores keyed by metric name.
    """

    demand_reason: str
    overlap_reason: str
    selection_reason: str
    conflict_note: str | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the reasoning to a JSON-friendly dict.

        Returns:
            dict[str, Any]: Reasoning fields with a shallow copy of score_breakdown.

        Example:
            >>> r = SessionReasoning("high demand", "3 players free", "Ranked #1")
            >>> r.to_dict()["selection_reason"]
            'Ranked #1'
        """
        return {
            "demand_reason": self.demand_reason,
            "overlap_reason": self.overlap_reason,
            "selection_reason": self.selection_reason,
            "conflict_note": self.conflict_note,
            "score_breakdown": dict(self.score_breakdown),
        }


@dataclass(slots=True)
class CandidateSession:
    """A scored (game, slot, location) scheduling candidate.

    Produced by the scoring layer and consumed by the selection and
    explanation layers.  Fields below ``viable`` are only meaningful
    when ``viable`` is ``True``.

    Attributes:
        game: Game identifier.
        slot: Slot identifier.
        location: Location identifier.
        eligible_players: Players who want the game, are free at the slot,
            and prefer the location.
        eligible_count: Length of ``eligible_players`` (cached for speed).
        viability_score: Weighted composite score in ``[0, 1]``.
        score_breakdown: Per-component scores (demand, popularity, etc.).
        viable: ``False`` when a hard filter was triggered.
        rejection_reason: Human-readable reason for non-viability, or ``None``.
        reasoning: Explainability trace attached after selection, or ``None``.
        is_overflow: ``True`` when this is a second table at the same slot.
        suggestion_reason: Why this near-miss didn't make the schedule.
    """

    game: str
    slot: str
    location: str
    eligible_players: set[str] = field(default_factory=set)
    eligible_count: int = 0
    viability_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)
    viable: bool = True
    rejection_reason: str | None = None
    reasoning: SessionReasoning | None = None
    is_overflow: bool = False
    suggestion_reason: str | None = None


@dataclass(slots=True)
class SelectionResult:
    """Return type for the session selection process."""

    selected: list[CandidateSession] = field(default_factory=list)
    suggestions: list[CandidateSession] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the selection result to a JSON-friendly dict.

        Returns:
            dict[str, Any]: Serialized result fields.
        """
        return {
            "game": self.game,
            "slot": self.slot,
            "location": self.location,
            "eligible_players": sorted(self.eligible_players),
            "eligible_count": self.eligible_count,
            "viability_score": self.viability_score,
            "score_breakdown": dict(self.score_breakdown),
            "viable": self.viable,
            "rejection_reason": self.rejection_reason,
            "reasoning": self.reasoning.to_dict() if self.reasoning else None,
        }
