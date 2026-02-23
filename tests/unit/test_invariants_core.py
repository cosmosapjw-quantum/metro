from __future__ import annotations

import pytest

from metroflow.sim.invariants import (
    ConservationSnapshot,
    check_capacity_violation_flags,
    check_conservation_hook,
    check_non_negative_queue,
)


def test_conservation_hook_passes_when_totals_reconcile():
    snapshot = ConservationSnapshot(
        generated_total=10,
        pending_trip_requests=3,
        active_agents=2,
        completed_trips_total=4,
        failed_trips_total=1,
    )

    assert snapshot.reconciled_total == 10
    assert check_conservation_hook(snapshot) == ()


def test_conservation_hook_reports_mismatch_with_details():
    snapshot = ConservationSnapshot(
        generated_total=10,
        pending_trip_requests=3,
        active_agents=2,
        completed_trips_total=3,
        failed_trips_total=1,
    )

    violations = check_conservation_hook(snapshot)
    assert len(violations) == 1
    violation = violations[0]
    assert violation.code == "conservation_mismatch"
    assert violation.check_name == "conservation"
    assert violation.details["generated_total"] == 10
    assert violation.details["reconciled_total"] == 9
    assert violation.details["delta"] == 1


def test_non_negative_queue_check_passes_for_non_negative_values():
    assert check_non_negative_queue([0.0, 1.5, 2.0]) == ()


def test_non_negative_queue_check_reports_first_negative_and_count():
    violations = check_non_negative_queue(
        [0.5, -0.25, 3.0, -1.0],
        field_name="queue_vehicles",
    )
    assert len(violations) == 1
    violation = violations[0]
    assert violation.code == "negative_queue_detected"
    assert violation.check_name == "non_negative_queue"
    assert violation.details["field_name"] == "queue_vehicles"
    assert violation.details["negative_count"] == 2
    assert violation.details["first_negative_index"] == 1
    assert violation.details["min_value"] == pytest.approx(-1.0)


def test_capacity_violation_flag_check_passes_when_counts_match():
    violations = check_capacity_violation_flags(
        outflow_values=[1.0, 3.0, 2.0],
        effective_capacity_values=[1.0, 2.0, 2.0],
        flagged_count=1,
    )
    assert violations == ()


def test_capacity_violation_flag_check_reports_mismatch():
    violations = check_capacity_violation_flags(
        outflow_values=[1.2, 3.5, 0.5],
        effective_capacity_values=[1.0, 2.0, 1.0],
        flagged_count=1,
    )
    assert len(violations) == 1
    violation = violations[0]
    assert violation.code == "capacity_flag_count_mismatch"
    assert violation.check_name == "capacity_flags"
    assert violation.details["observed_exceed_count"] == 2
    assert violation.details["flagged_count"] == 1


def test_capacity_violation_flag_check_raises_on_shape_mismatch():
    with pytest.raises(ValueError):
        check_capacity_violation_flags(
            outflow_values=[1.0, 2.0],
            effective_capacity_values=[1.0],
            flagged_count=0,
        )
