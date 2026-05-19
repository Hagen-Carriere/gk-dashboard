"""
Tests for output JSON schema validation (04_generate_viz_data.py).

Loads generated JSON files and validates:
    - All required fields are present
    - Field types match the schema (no strings where numbers expected, etc.)
    - Enum values are within the allowed set
    - Numeric ranges are sane (percentages 0-1, coordinates in bounds)
    - Referential integrity (every keeper_id in shots.json exists in keepers.json)

These tests run as the final CI gate — if the pipeline produces valid
output, these pass. If a schema change breaks the contract, these catch it
before the frontend sees bad data.
"""

import pytest


class TestCompetitionsJson:
    def test_required_fields(self) -> None:
        pytest.skip("TODO: Milestone 2")

    def test_at_least_one_competition(self) -> None:
        pytest.skip("TODO: Milestone 2")


class TestKeepersJson:
    def test_required_fields(self) -> None:
        pytest.skip("TODO: Milestone 2")

    def test_save_percentage_range(self) -> None:
        """save_percentage should be 0-1 for all keepers."""
        pytest.skip("TODO: Milestone 2")

    def test_minutes_above_threshold(self) -> None:
        """All listed keepers should meet the min_minutes_threshold."""
        pytest.skip("TODO: Milestone 2")


class TestShotsJson:
    def test_shot_outcomes_valid(self) -> None:
        """Every shot_outcome should be in the ShotOutcome enum."""
        pytest.skip("TODO: Milestone 2")

    def test_coordinates_in_bounds(self) -> None:
        """shot_location x: 0-120, y: 0-80. goal_frame gf_x: 0-8, gf_y: 0-8."""
        pytest.skip("TODO: Milestone 2")

    def test_xg_range(self) -> None:
        """statsbomb_xg should be 0.0-1.0."""
        pytest.skip("TODO: Milestone 2")


class TestDistributionJson:
    def test_pass_outcomes_valid(self) -> None:
        pytest.skip("TODO: Milestone 2")

    def test_pass_length_positive(self) -> None:
        pytest.skip("TODO: Milestone 2")


class TestSweepingJson:
    def test_action_types_valid(self) -> None:
        pytest.skip("TODO: Milestone 2")

    def test_distance_non_negative(self) -> None:
        pytest.skip("TODO: Milestone 2")


class TestSummaryJson:
    def test_radar_values_zero_to_one(self) -> None:
        """All radar profile values should be 0-1 (percentile ranks)."""
        pytest.skip("TODO: Milestone 2")

    def test_counts_non_negative(self) -> None:
        """No negative counts in shot stopping, distribution, or sweeping profiles."""
        pytest.skip("TODO: Milestone 2")
