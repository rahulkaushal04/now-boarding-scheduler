from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerConfig:
    """User-facing scheduler configuration."""

    target_sessions: int = 4
    max_tables_per_slot: int = 1
    max_repeats_per_week: int = 1

    def validate(self) -> list[str]:
        """Validate configuration values.

        Returns:
            list[str]: Validation error messages.
        """
        errors: list[str] = []

        fields = {
            "Target sessions": self.target_sessions,
            "Max tables per slot": self.max_tables_per_slot,
            "Max repeats per week": self.max_repeats_per_week,
        }

        for label, value in fields.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"{label} must be a positive integer")

        return errors
