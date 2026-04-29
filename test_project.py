"""
test_project.py — pytest test suite for Charis Properties Tracker
==================================================================
Tests cover the four core functions:
  - register_project
  - log_milestone
  - calculate_roi
  - flag_delays
  - generate_report

Run with:  pytest test_project.py -v
"""

import os
import csv
import pytest
from datetime import date, timedelta

from project import (
    register_project,
    log_milestone,
    calculate_roi,
    flag_delays,
    generate_report,
    MILESTONES,
)


# ─────────────────────────────────────────────
# FIXTURES — reusable test data
# ─────────────────────────────────────────────

@pytest.fixture
def sample_project():
    """A valid, freshly registered project."""
    future_date = (date.today() + timedelta(days=730)).isoformat()  # 2 years out
    return register_project(
        name="Charis Ruaka Phase 1",
        location="Ruaka, Nairobi",
        total_units=48,
        entry_price_kes=4_500_000.0,
        target_date=future_date,
    )


@pytest.fixture
def overdue_project():
    """A project whose target date has already passed — should flag RED."""
    past_date = (date.today() - timedelta(days=10)).isoformat()
    created_date = (date.today() - timedelta(days=400)).isoformat()
    p = register_project(
        name="Ghost Heights",
        location="Syokimau",
        total_units=20,
        entry_price_kes=3_000_000.0,
        target_date=past_date,
    )
    p["created_at"] = created_date
    return p


# ─────────────────────────────────────────────
# TEST: register_project
# ─────────────────────────────────────────────

def test_register_project_returns_dict(sample_project):
    assert isinstance(sample_project, dict)


def test_register_project_fields(sample_project):
    """All required keys must be present."""
    required_keys = ["id", "name", "location", "total_units",
                     "entry_price_kes", "target_date", "milestones", "status"]
    for key in required_keys:
        assert key in sample_project, f"Missing key: {key}"


def test_register_project_values(sample_project):
    assert sample_project["name"] == "Charis Ruaka Phase 1"
    assert sample_project["location"] == "Ruaka, Nairobi"
    assert sample_project["total_units"] == 48
    assert sample_project["entry_price_kes"] == 4_500_000.0


def test_register_project_empty_name():
    """Empty name should raise ValueError."""
    with pytest.raises(ValueError, match="name"):
        register_project("", "Ruaka", 10, 1_000_000, "2027-01-01")


def test_register_project_zero_units():
    with pytest.raises(ValueError, match="units"):
        register_project("Test", "Ruaka", 0, 1_000_000, "2027-01-01")


def test_register_project_negative_price():
    with pytest.raises(ValueError, match="price"):
        register_project("Test", "Ruaka", 10, -500_000, "2027-01-01")


def test_register_project_bad_date():
    """Malformed date should raise ValueError."""
    with pytest.raises(ValueError, match="date"):
        register_project("Test", "Ruaka", 10, 1_000_000, "01-01-2027")


# ─────────────────────────────────────────────
# TEST: log_milestone
# ─────────────────────────────────────────────

def test_log_milestone_valid(sample_project):
    updated = log_milestone(sample_project, "Foundation", 100.0, verified=True)
    assert "Foundation" in updated["milestones"]
    assert updated["milestones"]["Foundation"]["completion_pct"] == 100.0
    assert updated["milestones"]["Foundation"]["verified"] is True


def test_log_milestone_unverified(sample_project):
    updated = log_milestone(sample_project, "Superstructure", 55.0)
    assert updated["milestones"]["Superstructure"]["verified"] is False


def test_log_milestone_invalid_name(sample_project):
    with pytest.raises(ValueError, match="Milestone"):
        log_milestone(sample_project, "Painting", 50.0)


def test_log_milestone_pct_over_100(sample_project):
    with pytest.raises(ValueError, match="percentage"):
        log_milestone(sample_project, "Foundation", 150.0)


def test_log_milestone_pct_negative(sample_project):
    with pytest.raises(ValueError, match="percentage"):
        log_milestone(sample_project, "Foundation", -5.0)


def test_log_milestone_zero_pct(sample_project):
    """0% is valid — work has just started."""
    updated = log_milestone(sample_project, "Land Acquisition", 0.0)
    assert updated["milestones"]["Land Acquisition"]["completion_pct"] == 0.0


# ─────────────────────────────────────────────
# TEST: calculate_roi
# ─────────────────────────────────────────────

def test_calculate_roi_returns_dict():
    result = calculate_roi(4_500_000, 0.12, 2.0, 0.08)
    assert isinstance(result, dict)


def test_calculate_roi_keys():
    result = calculate_roi(4_500_000, 0.12, 2.0, 0.08)
    expected_keys = ["entry_price_kes", "projected_value_kes", "capital_gain_kes",
                     "rental_income_kes", "total_return_kes", "roi_pct", "annualised_roi_pct"]
    for key in expected_keys:
        assert key in result, f"Missing key: {key}"


def test_calculate_roi_projected_value_greater_than_entry():
    """With positive appreciation, projected value must exceed entry price."""
    result = calculate_roi(3_000_000, 0.10, 2.0)
    assert result["projected_value_kes"] > result["entry_price_kes"]


def test_calculate_roi_zero_appreciation():
    """Zero appreciation: projected value equals entry price."""
    result = calculate_roi(2_000_000, 0.0, 2.0, 0.0)
    assert result["projected_value_kes"] == pytest.approx(2_000_000.0)
    assert result["capital_gain_kes"] == pytest.approx(0.0)


def test_calculate_roi_correct_values():
    """Manual spot-check: 4.5M at 12% for 2 years, 8% yield."""
    result = calculate_roi(4_500_000, 0.12, 2.0, 0.08)
    expected_projected = 4_500_000 * (1.12 ** 2)
    assert result["projected_value_kes"] == pytest.approx(expected_projected, rel=1e-3)


def test_calculate_roi_roi_positive():
    result = calculate_roi(5_000_000, 0.10, 3.0, 0.07)
    assert result["roi_pct"] > 0


def test_calculate_roi_zero_entry_raises():
    with pytest.raises(ValueError, match="Entry price"):
        calculate_roi(0, 0.10, 2.0)


def test_calculate_roi_negative_years_raises():
    with pytest.raises(ValueError, match="Years"):
        calculate_roi(1_000_000, 0.10, -1)


def test_calculate_roi_negative_yield_raises():
    with pytest.raises(ValueError, match="yield"):
        calculate_roi(1_000_000, 0.10, 2.0, -0.05)


# ─────────────────────────────────────────────
# TEST: flag_delays
# ─────────────────────────────────────────────

def test_flag_delays_green_new_project(sample_project):
    """A brand new project with no milestones, far from deadline — should be GREEN."""
    status = flag_delays(sample_project)
    assert status == "GREEN"


def test_flag_delays_red_overdue(overdue_project):
    """A project past its target date must be RED."""
    status = flag_delays(overdue_project)
    assert status == "RED"


def test_flag_delays_returns_valid_status(sample_project):
    status = flag_delays(sample_project)
    assert status in ("GREEN", "AMBER", "RED")


def test_flag_delays_amber_behind():
    """Simulate a project that's 10% behind expected progress."""
    start = (date.today() - timedelta(days=200)).isoformat()
    target = (date.today() + timedelta(days=100)).isoformat()
    p = register_project("Amber Test", "Kileleshwa", 10, 2_000_000, target)
    p["created_at"] = start
    # Log minimal progress even though 2/3 of time has elapsed
    p = log_milestone(p, "Land Acquisition", 100.0)
    p = log_milestone(p, "Foundation", 20.0)  # Artificially behind
    status = flag_delays(p)
    assert status in ("AMBER", "RED")  # Should not be GREEN


# ─────────────────────────────────────────────
# TEST: generate_report
# ─────────────────────────────────────────────

def test_generate_report_creates_file(sample_project, tmp_path):
    output = str(tmp_path / "test_report.csv")
    result = generate_report([sample_project], output)
    assert os.path.exists(result)


def test_generate_report_correct_headers(sample_project, tmp_path):
    output = str(tmp_path / "test_report.csv")
    generate_report([sample_project], output)
    with open(output, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
    assert "Project Name" in headers
    assert "Delay Status" in headers
    assert "Projected ROI (%)" in headers


def test_generate_report_correct_row_count(tmp_path):
    future = (date.today() + timedelta(days=500)).isoformat()
    p1 = register_project("Project A", "Ruaka", 10, 4_000_000, future)
    p2 = register_project("Project B", "Juja", 20, 3_500_000, future)
    output = str(tmp_path / "multi_report.csv")
    generate_report([p1, p2], output)
    with open(output, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2


def test_generate_report_empty_raises():
    with pytest.raises(ValueError, match="No projects"):
        generate_report([])