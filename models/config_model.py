from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerConfig:
    """User-facing scheduler configuration."""

    max_repeats_per_week: int = 1

    def validate(self) -> list[str]:
        """Validate configuration values.

        Returns:
            list[str]: Validation error messages.
        """
        errors: list[str] = []

        fields = {
            "Max repeats per week": self.max_repeats_per_week,
        }

        for label, value in fields.items():
            if not isinstance(value, int) or value < 1:
                errors.append(f"{label} must be a positive integer")

        return errors
