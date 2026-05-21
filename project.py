"""
Charis Properties – Off-Plan Investment Tracker
================================================
Ann Njeri Mucheke
Nairobi, Kenya  |  2026

A command-line tool that:
  1. Registers off-plan development projects
  2. Logs construction milestones with verification status
  3. Calculates projected ROI for investors
  4. Flags delayed or at-risk projects
  5. Generates a CSV investor report

Usage:
    python project.py
"""

import csv
import json
import os
import sys
from datetime import datetime, date

# ─────────────────────────────────────────────
# Optional rich library for prettier output.
# Falls back to plain text if not installed.
# ─────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    RICH = True
    console = Console()
except ImportError:
    RICH = False

DATA_FILE = "projects.json"
MILESTONES = ["Land Acquisition", "Foundation", "Superstructure", "Roofing", "Finishes", "Handover"]


# ─────────────────────────────────────────────
# 1. PROJECT REGISTRATION
# ─────────────────────────────────────────────

def register_project(name: str, location: str, total_units: int,
                     entry_price_kes: float, target_date: str) -> dict:
    """
    Create and return a new project record dictionary.

    Args:
        name:             Project name (e.g. "Charis Ruaka Phase 1")
        location:         Satellite town or area (e.g. "Ruaka, Nairobi")
        total_units:      Number of units in the development
        entry_price_kes:  Off-plan price per unit in KES
        target_date:      Target handover date in YYYY-MM-DD format

    Returns:
        A dict representing the new project.

    Raises:
        ValueError: If any argument is invalid.
    """
    if not name or not isinstance(name, str):
        raise ValueError("Project name must be a non-empty string.")
    if total_units <= 0:
        raise ValueError("Total units must be a positive integer.")
    if entry_price_kes <= 0:
        raise ValueError("Entry price must be a positive number.")

    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Target date must be in YYYY-MM-DD format.")

    project = {
        "id": name.lower().replace(" ", "_") + "_" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "name": name,
        "location": location,
        "total_units": total_units,
        "entry_price_kes": entry_price_kes,
        "target_date": target_date,
        "created_at": date.today().isoformat(),
        "milestones": {},
        "status": "Active",
    }
    return project


# ─────────────────────────────────────────────
# 2. MILESTONE LOGGING
# ─────────────────────────────────────────────

def log_milestone(project: dict, milestone_name: str,
                  completion_pct: float, verified: bool = False) -> dict:
    """
    Record a construction milestone on a project.

    Args:
        project:         The project dict (from register_project or load).
        milestone_name:  One of the MILESTONES list values.
        completion_pct:  Percentage complete (0–100).
        verified:        Whether this milestone has been AI/drone-verified.

    Returns:
        Updated project dict.

    Raises:
        ValueError: If milestone name is invalid or percentage out of range.
    """
    if milestone_name not in MILESTONES:
        raise ValueError(f"Milestone must be one of: {', '.join(MILESTONES)}")
    if not (0 <= completion_pct <= 100):
        raise ValueError("Completion percentage must be between 0 and 100.")

    project["milestones"][milestone_name] = {
        "completion_pct": round(completion_pct, 1),
        "verified": verified,
        "logged_at": date.today().isoformat(),
    }
    return project


# ─────────────────────────────────────────────
# 3. ROI CALCULATION
# ─────────────────────────────────────────────

def calculate_roi(entry_price_kes: float, appreciation_rate: float,
                  years: float, rental_yield: float = 0.0) -> dict:
    """
    Calculate projected Return on Investment for an off-plan unit.

    Off-plan buyers typically enter at 20–30% below completed market value.
    This function models:
      - Capital appreciation over the build period
      - Optional annual rental yield once completed

    Args:
        entry_price_kes:   Purchase price in KES.
        appreciation_rate: Annual appreciation rate as a decimal (e.g. 0.12 for 12%).
        years:             Build / holding period in years.
        rental_yield:      Annual rental yield as a decimal (e.g. 0.08 for 8%).

    Returns:
        A dict with projected_value, capital_gain, rental_income, total_return,
        roi_pct, and annualised_roi_pct.

    Raises:
        ValueError: If any numeric argument is invalid.
    """
    if entry_price_kes <= 0:
        raise ValueError("Entry price must be positive.")
    if appreciation_rate < 0:
        raise ValueError("Appreciation rate cannot be negative.")
    if years <= 0:
        raise ValueError("Years must be positive.")
    if rental_yield < 0:
        raise ValueError("Rental yield cannot be negative.")

    projected_value = entry_price_kes * ((1 + appreciation_rate) ** years)
    capital_gain = projected_value - entry_price_kes

    # Rental income starts after completion (approximated as end of build period)
    rental_income = entry_price_kes * rental_yield * years

    total_return = capital_gain + rental_income
    roi_pct = (total_return / entry_price_kes) * 100
    annualised_roi_pct = roi_pct / years if years > 0 else 0

    return {
        "entry_price_kes": round(entry_price_kes, 2),
        "projected_value_kes": round(projected_value, 2),
        "capital_gain_kes": round(capital_gain, 2),
        "rental_income_kes": round(rental_income, 2),
        "total_return_kes": round(total_return, 2),
        "roi_pct": round(roi_pct, 2),
        "annualised_roi_pct": round(annualised_roi_pct, 2),
    }


# ─────────────────────────────────────────────
# 4. DELAY DETECTION
# ─────────────────────────────────────────────

def flag_delays(project: dict) -> str:
    """
    Analyse a project's overall progress and compare to target date.

    Returns a status string:
        "GREEN"  – On track (≥ expected progress)
        "AMBER"  – Minor delay (5–15% behind expected)
        "RED"    – Significant delay (> 15% behind expected, or overdue)

    Args:
        project: A project dict.

    Returns:
        One of "GREEN", "AMBER", or "RED".
    """
    today = date.today()

    try:
        target = date.fromisoformat(project["target_date"])
        created = date.fromisoformat(project["created_at"])
    except (KeyError, ValueError):
        return "AMBER"  # Incomplete data — flag cautiously

    # If already past handover date, immediately RED
    if today > target:
        return "RED"

    # Calculate expected progress based on elapsed time
    total_days = (target - created).days
    elapsed_days = (today - created).days
    expected_pct = (elapsed_days / total_days * 100) if total_days > 0 else 0

    # Average actual completion across logged milestones
    milestones = project.get("milestones", {})
    if not milestones:
        actual_pct = 0.0
    else:
        actual_pct = sum(m["completion_pct"] for m in milestones.values()) / len(MILESTONES)

    gap = expected_pct - actual_pct

    if gap <= 5:
        return "GREEN"
    elif gap <= 15:
        return "AMBER"
    else:
        return "RED"


# ─────────────────────────────────────────────
# 5. REPORT GENERATION
# ─────────────────────────────────────────────

def generate_report(projects: list, output_file: str = "charis_report.csv") -> str:
    """
    Export a summary of all projects to a CSV file.

    Each row contains: project name, location, units, entry price,
    target date, milestone progress, delay status, and ROI projection.

    Args:
        projects:    List of project dicts.
        output_file: Path to write the CSV report.

    Returns:
        The path to the generated file.

    Raises:
        ValueError: If projects list is empty.
    """
    if not projects:
        raise ValueError("No projects to report on.")

    fieldnames = [
        "Project Name", "Location", "Total Units", "Entry Price (KES)",
        "Target Date", "Milestones Logged", "Overall Progress (%)",
        "Delay Status", "Projected ROI (%)", "Projected Value (KES)"
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for p in projects:
            milestones = p.get("milestones", {})
            overall_pct = (
                sum(m["completion_pct"] for m in milestones.values()) / len(MILESTONES)
                if milestones else 0.0
            )

            roi_data = calculate_roi(
                entry_price_kes=p["entry_price_kes"],
                appreciation_rate=0.12,   # 12% annual — Kenyan satellite town benchmark
                years=2.0,
                rental_yield=0.08,        # 8% yield — residential standard
            )

            status = flag_delays(p)

            writer.writerow({
                "Project Name": p["name"],
                "Location": p["location"],
                "Total Units": p["total_units"],
                "Entry Price (KES)": f"{p['entry_price_kes']:,.0f}",
                "Target Date": p["target_date"],
                "Milestones Logged": len(milestones),
                "Overall Progress (%)": f"{overall_pct:.1f}",
                "Delay Status": status,
                "Projected ROI (%)": roi_data["roi_pct"],
                "Projected Value (KES)": f"{roi_data['projected_value_kes']:,.0f}",
            })

    return output_file


# ─────────────────────────────────────────────
# DATA PERSISTENCE HELPERS
# ─────────────────────────────────────────────

def load_projects() -> list:
    """Load all projects from the local JSON data file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_projects(projects: list) -> None:
    """Persist the projects list to the local JSON data file."""
    with open(DATA_FILE, "w") as f:
        json.dump(projects, f, indent=2)


# ─────────────────────────────────────────────
# CLI DISPLAY HELPERS
# ─────────────────────────────────────────────

STATUS_COLORS = {"GREEN": "✅", "AMBER": "⚠️ ", "RED": "🔴"}


def print_project_table(projects: list) -> None:
    """Print all projects in a formatted table."""
    if not projects:
        print("\n  No projects registered yet.\n")
        return

    if RICH:
        table = Table(title="Charis Properties — Project Overview", show_lines=True)
        table.add_column("Project", style="bold cyan")
        table.add_column("Location")
        table.add_column("Units", justify="right")
        table.add_column("Entry Price (KES)", justify="right")
        table.add_column("Target Date")
        table.add_column("Progress")
        table.add_column("Status")

        for p in projects:
            milestones = p.get("milestones", {})
            overall = (
                sum(m["completion_pct"] for m in milestones.values()) / len(MILESTONES)
                if milestones else 0.0
            )
            status = flag_delays(p)
            icon = STATUS_COLORS.get(status, "")
            progress_bar = _progress_bar(overall)

            table.add_row(
                p["name"], p["location"], str(p["total_units"]),
                f"{p['entry_price_kes']:,.0f}",
                p["target_date"], progress_bar,
                f"{icon} {status}"
            )
        console.print(table)
    else:
        # Plain text fallback
        header = f"{'Project':<30} {'Location':<20} {'Units':>5} {'Progress':>10} {'Status':<8}"
        print("\n" + header)
        print("-" * len(header))
        for p in projects:
            milestones = p.get("milestones", {})
            overall = (
                sum(m["completion_pct"] for m in milestones.values()) / len(MILESTONES)
                if milestones else 0.0
            )
            status = flag_delays(p)
            print(f"{p['name']:<30} {p['location']:<20} {p['total_units']:>5} {overall:>9.1f}% {status:<8}")
        print()


def _progress_bar(pct: float, width: int = 12) -> str:
    """Return a simple ASCII progress bar string."""
    filled = int(pct / 100 * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {pct:.0f}%"


def print_roi(roi: dict) -> None:
    """Print ROI results in a readable format."""
    print("\n  ── Projected ROI ──────────────────────────")
    print(f"  Entry Price:        KES {roi['entry_price_kes']:>15,.2f}")
    print(f"  Projected Value:    KES {roi['projected_value_kes']:>15,.2f}")
    print(f"  Capital Gain:       KES {roi['capital_gain_kes']:>15,.2f}")
    print(f"  Rental Income:      KES {roi['rental_income_kes']:>15,.2f}")
    print(f"  Total Return:       KES {roi['total_return_kes']:>15,.2f}")
    print(f"  ROI:                    {roi['roi_pct']:>14.2f}%")
    print(f"  Annualised ROI:         {roi['annualised_roi_pct']:>14.2f}%")
    print()


# ─────────────────────────────────────────────
# MAIN — CLI MENU
# ─────────────────────────────────────────────

def main():
    """Main entry point — interactive CLI menu for Charis Properties Tracker."""

    if RICH:
        console.print(Panel.fit(
            "[bold gold1]🏗  Charis Properties[/bold gold1]\n"
            "[dim]Transparency-First Off-Plan Investment Tracker[/dim]\n"
            "[dim italic]Nairobi, Kenya  |  2026[/dim italic]",
            border_style="gold1"
        ))
    else:
        print("\n" + "=" * 50)
        print("  🏗  CHARIS PROPERTIES")
        print("  Off-Plan Investment Tracker — Nairobi, Kenya")
        print("=" * 50 + "\n")

    projects = load_projects()

    while True:
        print("\nMain Menu")
        print("  1. View all projects")
        print("  2. Register new project")
        print("  3. Log construction milestone")
        print("  4. Calculate ROI for a project")
        print("  5. Check project status / delays")
        print("  6. Generate investor report (CSV)")
        print("  0. Exit")

        choice = input("\nEnter choice: ").strip()

        # ── 1. VIEW PROJECTS ──────────────────────
        if choice == "1":
            print_project_table(projects)

        # ── 2. REGISTER PROJECT ───────────────────
        elif choice == "2":
            print("\n── Register New Project ──")
            try:
                name = input("  Project name: ").strip()
                location = input("  Location (e.g. Ruaka, Nairobi): ").strip()
                units = int(input("  Total units: ").strip())
                price = float(input("  Entry price per unit (KES): ").strip())
                target = input("  Target handover date (YYYY-MM-DD): ").strip()

                project = register_project(name, location, units, price, target)
                projects.append(project)
                save_projects(projects)
                print(f"\n  ✅  Project '{name}' registered successfully.")
            except ValueError as e:
                print(f"\n  ❌  Error: {e}")

        # ── 3. LOG MILESTONE ──────────────────────
        elif choice == "3":
            if not projects:
                print("\n  No projects found. Register one first.")
                continue

            print("\n── Log Milestone ──")
            for i, p in enumerate(projects):
                print(f"  {i + 1}. {p['name']} ({p['location']})")

            try:
                idx = int(input("\n  Select project number: ").strip()) - 1
                if not (0 <= idx < len(projects)):
                    print("  Invalid selection.")
                    continue

                print(f"\n  Milestones: {', '.join(MILESTONES)}")
                milestone = input("  Milestone name: ").strip().title()
                pct = float(input("  Completion %: ").strip())
                verified_input = input("  AI/Drone verified? (y/n): ").strip().lower()
                verified = verified_input == "y"

                projects[idx] = log_milestone(projects[idx], milestone, pct, verified)
                save_projects(projects)

                badge = "✅ Verified" if verified else "📋 Unverified"
                print(f"\n  Milestone '{milestone}' logged at {pct}% — {badge}")

            except ValueError as e:
                print(f"\n  ❌  Error: {e}")

        # ── 4. CALCULATE ROI ──────────────────────
        elif choice == "4":
            if not projects:
                print("\n  No projects found.")
                continue

            print("\n── ROI Calculator ──")
            for i, p in enumerate(projects):
                print(f"  {i + 1}. {p['name']} — KES {p['entry_price_kes']:,.0f} per unit")

            try:
                idx = int(input("\n  Select project: ").strip()) - 1
                if not (0 <= idx < len(projects)):
                    print("  Invalid selection.")
                    continue

                p = projects[idx]
                print(f"\n  Using entry price: KES {p['entry_price_kes']:,.0f}")
                app_rate = float(input("  Annual appreciation rate (e.g. 0.12 for 12%): ").strip())
                years = float(input("  Holding period in years: ").strip())
                yield_rate = float(input("  Annual rental yield (e.g. 0.08 for 8%): ").strip())

                roi = calculate_roi(p["entry_price_kes"], app_rate, years, yield_rate)
                print_roi(roi)

            except ValueError as e:
                print(f"\n  ❌  Error: {e}")

        # ── 5. DELAY STATUS ───────────────────────
        elif choice == "5":
            if not projects:
                print("\n  No projects found.")
                continue

            print("\n── Project Status ──")
            for p in projects:
                status = flag_delays(p)
                icon = STATUS_COLORS.get(status, "")
                milestones = p.get("milestones", {})
                overall = (
                    sum(m["completion_pct"] for m in milestones.values()) / len(MILESTONES)
                    if milestones else 0.0
                )
                print(f"\n  {p['name']} ({p['location']})")
                print(f"    Target:   {p['target_date']}")
                print(f"    Progress: {_progress_bar(overall)}")
                print(f"    Status:   {icon} {status}")

                # Show individual milestones
                if milestones:
                    print("    Milestones:")
                    for ms_name, ms_data in milestones.items():
                        vbadge = "✅" if ms_data["verified"] else "📋"
                        print(f"      {vbadge} {ms_name}: {ms_data['completion_pct']}% ({ms_data['logged_at']})")

        # ── 6. GENERATE REPORT ────────────────────
        elif choice == "6":
            if not projects:
                print("\n  No projects to report on.")
                continue

            try:
                filename = input("\n  Output filename (default: charis_report.csv): ").strip()
                if not filename:
                    filename = "charis_report.csv"
                path = generate_report(projects, filename)
                print(f"\n  ✅  Report saved to: {path}")
            except ValueError as e:
                print(f"\n  ❌  Error: {e}")

        # ── 0. EXIT ───────────────────────────────
        elif choice == "0":
            print("\n  Karibu tena. Goodbye.\n")
            sys.exit(0)

        else:
            print("  Invalid choice. Please enter 0–6.")


if __name__ == "__main__":
    main()
