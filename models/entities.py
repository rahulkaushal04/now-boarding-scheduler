"""Domain entities for the scheduler: players, games, slots, and sessions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Player:
    id: str
    heavy_prefs: set[str] = field(default_factory=set)
    medium_prefs: set[str] = field(default_factory=set)
    all_prefs: set[str] = field(default_factory=set)
    location_prefs: set[str] = field(default_factory=set)
    time_availability: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        """Serialize player to a JSON-friendly dict."""
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
    id: str
    weight_class: str  # "heavy" | "medium"
    min_players: int = 1
    owner: str | None = None
    allowed_days: set[str] | None = None
    location_lock: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize game to a JSON-friendly dict."""
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
    id: str
    day: str
    time: str

    def to_dict(self) -> dict[str, str]:
        """Serialize slot to dict."""
        return {"id": self.id, "day": self.day, "time": self.time}


@dataclass(slots=True)
class Location:
    id: str

    def to_dict(self) -> dict[str, str]:
        """Serialize location to dict."""
        return {"id": self.id}


@dataclass(slots=True)
class SessionReasoning:
    demand_reason: str
    overlap_reason: str
    selection_reason: str
    conflict_note: str | None = None
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize reasoning details."""
        return {
            "demand_reason": self.demand_reason,
            "overlap_reason": self.overlap_reason,
            "selection_reason": self.selection_reason,
            "conflict_note": self.conflict_note,
            "score_breakdown": dict(self.score_breakdown),
        }


@dataclass(slots=True)
class CandidateSession:
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
        """Serialize candidate session."""
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
