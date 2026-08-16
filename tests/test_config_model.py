"""Tests for models/config_model.py — SchedulerConfig."""

from __future__ import annotations

from models.config_model import SchedulerConfig


class TestDefaults:
    def test_default_min_players_is_two(self):
        """A single interested player isn't enough to justify opening a
        table — two is the realistic floor for a "session" at all."""
        assert SchedulerConfig().default_min_players == 2

    def test_revenue_weights_default_neutral(self):
        """No price data exists in the poll CSVs, so weight classes must
        not be assumed to differ in revenue unless explicitly configured."""
        config = SchedulerConfig()
        assert config.revenue_weight("heavy") == 1.0
        assert config.revenue_weight("medium") == 1.0
        assert config.revenue_weight("unknown") == 1.0


class TestTableCapacity:
    def test_falls_back_to_max_tables_per_slot(self):
        config = SchedulerConfig(max_tables_per_slot=3)
        assert config.table_capacity("HSR Layout") == 3

    def test_per_location_override(self):
        config = SchedulerConfig(
            max_tables_per_slot=2, tables_per_location={"HSR Layout": 4}
        )
        assert config.table_capacity("HSR Layout") == 4
        assert config.table_capacity("Jayanagar") == 2


class TestValidate:
    def test_valid_config_has_no_errors(self):
        assert SchedulerConfig().validate() == []

    def test_negative_max_repeats_is_invalid(self):
        errors = SchedulerConfig(max_repeats_per_week=0).validate()
        assert any("repeats" in e.lower() for e in errors)

    def test_negative_table_capacity_override_is_invalid(self):
        errors = SchedulerConfig(tables_per_location={"HSR Layout": 0}).validate()
        assert any("HSR Layout" in e for e in errors)

    def test_zero_revenue_weight_is_invalid(self):
        errors = SchedulerConfig(revenue_weight_heavy=0.0).validate()
        assert any("revenue weight" in e.lower() for e in errors)
