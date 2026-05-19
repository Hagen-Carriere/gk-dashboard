"""
Step 3: Compute derived goalkeeper metrics.

Takes the cleaned event DataFrames from step 2 and produces per-keeper
aggregated statistics:
    - Shot stopping: save %, xG faced, goals-minus-xG, zone breakdowns
    - Distribution: completion rates by length/type, direction splits
    - Sweeping: action counts, distance averages, claiming success rates
    - Radar profile: percentile ranks within the competition

Output: summary DataFrames ready for JSON serialization in step 4.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError("TODO: Milestone 2")


if __name__ == "__main__":
    main()
