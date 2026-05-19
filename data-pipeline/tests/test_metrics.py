"""
Tests for metric computation (03_compute_metrics.py).

Validates derived stats against hand-counted values for known matches.
The 2018 WC Final (France 4-2 Croatia, match_id TBD) is the primary
verification target because:
    - Known scoreline makes goal counts trivially verifiable
    - Lloris had a notable error (goal conceded from a bad touch)
    - Subasic conceded 4 goals from a mix of open play and set pieces
"""

import pytest


class TestSavePercentage:
    def test_basic_calculation(self) -> None:
        """save_pct = saves / shots_on_target. 5 saves, 7 on target = 0.714."""
        pytest.skip("TODO: Milestone 2")

    def test_zero_shots(self) -> None:
        """Keeper who faced 0 shots on target should have save_pct = None, not div/0."""
        pytest.skip("TODO: Milestone 2")


class TestGoalsMinusXG:
    def test_outperforming_keeper(self) -> None:
        """If xG faced = 3.5 and goals conceded = 2, goals_minus_xg = -1.5."""
        pytest.skip("TODO: Milestone 2")

    def test_underperforming_keeper(self) -> None:
        """If xG faced = 1.2 and goals conceded = 3, goals_minus_xg = 1.8."""
        pytest.skip("TODO: Milestone 2")


class TestCoordinateNormalization:
    def test_keeper_goal_at_x_zero(self) -> None:
        """After normalization, all keeper events should have location.x >= 0."""
        pytest.skip("TODO: Milestone 1")

    def test_shot_location_in_bounds(self) -> None:
        """All shot locations should be within 0-120 x, 0-80 y."""
        pytest.skip("TODO: Milestone 1")

    def test_goal_frame_coords_in_bounds(self) -> None:
        """Goal frame coords should be within 0-8 for both axes."""
        pytest.skip("TODO: Milestone 2")


class TestShotZoneClassification:
    def test_six_yard_box(self) -> None:
        """Shot at (3, 40) should classify as Six-Yard Box."""
        pytest.skip("TODO: Milestone 2")

    def test_box_central(self) -> None:
        """Shot at (12, 35) should classify as Box Central."""
        pytest.skip("TODO: Milestone 2")

    def test_outside_box(self) -> None:
        """Shot at (25, 40) should classify as Outside Box."""
        pytest.skip("TODO: Milestone 2")


class TestDistributionMetrics:
    def test_pass_length_categories(self) -> None:
        """Pass of length 20 = Short, 35 = Medium, 60 = Long."""
        pytest.skip("TODO: Milestone 2")

    def test_progressive_pass(self) -> None:
        """Pass from (10, 40) to (25, 35) advances 15 units = progressive."""
        pytest.skip("TODO: Milestone 2")

    def test_direction_classification(self) -> None:
        """End location y < 26.67 = Left, 26.67-53.33 = Center, > 53.33 = Right."""
        pytest.skip("TODO: Milestone 2")
