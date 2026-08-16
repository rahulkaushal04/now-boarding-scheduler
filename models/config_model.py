"""User-facing scheduler configuration model."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class SchedulerConfig:
    """User-facing scheduler configuration.

    Every field here is a genuine business input: either a physical fact
    about the cafés (table counts) or an explicit policy choice (rotation
    limits, per-head value of a session type). None of these values are
    used as tuning knobs for the optimizer's correctness — the optimizer
    solves to a proven optimum given whatever these say, so changing them
    changes the real-world problem being solved, not the solution quality
    for a fixed problem.

    Attributes:
        max_repeats_per_week: Maximum times a single game may be scheduled
            per week. A rotation policy, not a physical limit — prevents
            one popular game from crowding out its own repeat slots
            indefinitely even when tables are free.
        default_min_players: Default minimum players needed to run any
            game. Applied per game unless overridden in the Game Rules step.
        max_tables_per_slot: Hard ceiling on concurrent tables at a single
            (location, slot), used for every location unless overridden in
            ``tables_per_location``.
        tables_per_location: Optional per-location override of
            ``max_tables_per_slot``, keyed by location id (e.g.
            ``{"HSR Layout": 3, "Jayanagar": 2}``). Locations absent from
            this mapping fall back to ``max_tables_per_slot``. Left empty
            by default because the physical table count per café isn't
            derivable from poll data — it must be supplied by the operator.
        revenue_weight_heavy: Relative per-head revenue value of a heavy
            (long/complex) session, used only to rank otherwise-tied
            schedules. Defaults to 1.0 (no assumed difference from medium)
            because the poll data carries no price or duration figures —
            raise it only if heavy sessions are known to generate more
            spend per player (e.g. longer table occupancy, more food/drink
            orders).
        revenue_weight_medium: Relative per-head revenue value of a medium
            session. See ``revenue_weight_heavy``.
    """

    max_repeats_per_week: int = 2
    default_min_players: int = 2
    max_tables_per_slot: int = 2
    tables_per_location: dict[str, int] = field(default_factory=dict)
    revenue_weight_heavy: float = 1.0
    revenue_weight_medium: float = 1.0

    def table_capacity(self, location: str) -> int:
        """Return the table ceiling for *location*.

        Args:
            location (str): Location id.

        Returns:
            int: ``tables_per_location[location]`` if set, else
                ``max_tables_per_slot``.

        Example:
            >>> SchedulerConfig(max_tables_per_slot=2).table_capacity("HSR")
            2
        """
        return self.tables_per_location.get(location, self.max_tables_per_slot)

    def revenue_weight(self, weight_class: str) -> float:
        """Return the per-head revenue weight for a game's weight class.

        Args:
            weight_class (str): ``"heavy"`` or ``"medium"``.

        Returns:
            float: The configured revenue weight; defaults to 1.0 for any
                unrecognised class.

        Example:
            >>> SchedulerConfig().revenue_weight("heavy")
            1.0
        """
        if weight_class == "heavy":
            return self.revenue_weight_heavy
        if weight_class == "medium":
            return self.revenue_weight_medium
        return 1.0

    def validate(self) -> list[str]:
        """Validate configuration values.

        Returns:
            list[str]: Validation error messages; empty when all values are valid.

        Example:
            >>> SchedulerConfig(max_repeats_per_week=0).validate()
            ['Max repeats per week must be a positive integer']
        """
        errors: list[str] = []

        int_fields = {
            "Max repeats per week": self.max_repeats_per_week,
            "Default min players": self.default_min_players,
            "Max tables per slot": self.max_tables_per_slot,
        }
        for label, value in int_fields.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"{label} must be a positive integer")

        for loc, capacity in self.tables_per_location.items():
            if not isinstance(capacity, int) or capacity < 1:
                errors.append(f"Table capacity for {loc!r} must be a positive integer")

        for label, value in (
            ("Revenue weight (heavy)", self.revenue_weight_heavy),
            ("Revenue weight (medium)", self.revenue_weight_medium),
        ):
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"{label} must be a positive number")

        return errors
