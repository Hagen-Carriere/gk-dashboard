"""
Tests for data ingestion (01_ingest.py).

Validates:
    - Match counts per competition match expected totals
    - Event files load without parse errors
    - Lineup files contain goalkeeper entries
    - No null match_ids or player_ids in loaded data
"""

import pytest


class TestIngestion:
    def test_2018_wc_match_count(self) -> None:
        """2018 World Cup should have 64 matches."""
        pytest.skip("TODO: Milestone 1")

    def test_events_load_without_errors(self) -> None:
        """Every match event file should parse as valid JSON."""
        pytest.skip("TODO: Milestone 1")

    def test_lineups_contain_goalkeepers(self) -> None:
        """Every match lineup should have at least one GK per team."""
        pytest.skip("TODO: Milestone 1")

    def test_no_null_ids(self) -> None:
        """No null match_id or player_id in loaded data."""
        pytest.skip("TODO: Milestone 1")
