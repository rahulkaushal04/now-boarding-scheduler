"""User-facing scheduler configuration model."""

from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerConfig:
    """User-facing scheduler configuration.

    Attributes:
        max_repeats_per_week: Maximum times a single game may be scheduled per week.
        default_min_players: Default minimum players needed to run any game.
        max_tables_per_slot: Hard ceiling on tables at a single (location, slot).
    """

    max_repeats_per_week: int = 2
    default_min_players: int = 1
    max_tables_per_slot: int = 2

    def validate(self) -> list[str]:
        """Validate configuration values.

        Returns:
            list[str]: Validation error messages; empty when all values are valid.

        Example:
            >>> SchedulerConfig(max_repeats_per_week=0).validate()
            ['Max repeats per week must be a positive integer']
        """
        errors: list[str] = []

        fields = {
            "Max repeats per week": self.max_repeats_per_week,
            "Default min players": self.default_min_players,
            "Max tables per slot": self.max_tables_per_slot,
        }

        for label, value in fields.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"{label} must be a positive integer")

        return errors
