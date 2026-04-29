# Charis Properties — Off-Plan Investment Tracker

A Python Command Line Interface tool for tracking construction milestones, calculating projected ROI, and flagging delays on off-plan property developments in Kenya.

#### Video Demo: `<https://youtu.be/Grl6hVEllpQ>`

---

## Why This Exists

Buying an off-plan property in Kenya, that is, paying for a house before it's built, often means sending money and then waiting, sometimes for years, with very little information about what's actually happening on site. Developers send vague updates, projects stall, and investors have no reliable way to verify progress. This is especially painful for diaspora investors who can't just drive past the site on a weekend.

I built this tool to start addressing that problem. It won't fix everything on its own, but it gives a developer or investor a structured, data-driven way to register projects, record what has actually been built, check whether things are running on schedule, and export a summary they can share or review later.

**Key features:**
- Register off-plan development projects with price, location, and target handover date
- Log construction milestones across six defined stages with a verification flag
- Calculate projected ROI using compound appreciation and rental yield
- Automatically flag projects as GREEN, AMBER, or RED based on schedule progress
- Export a CSV report covering all tracked projects

---

## Project Structure

```
charis_tracker/
├── project.py          # Main application and all core functions
├── test_project.py     # pytest test suite (30 tests)
├── requirements.txt    # External dependencies
├── README.md           # This file
└── projects.json       # Auto-generated on first run, stores your data
```

---

## Installation & Usage

**Prerequisites:** Python 3.10 or higher.

```bash
# 1. Clone the repository
git clone https://github.com/<SCHECKS>/charis-properties.git
cd charis-properties

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the tracker
python project.py

# 4. Run the test suite
pytest test_project.py -v
```

On first run, `projects.json` is created automatically in the same folder. No database setup required.

---

## How It Works

`main()` opens an interactive numbered menu. Everything runs from there, you pick an option and the program handles input, validation, and saving.

`register_project()` builds a new project dictionary from a name, location, unit count, price in Kenyan shillings, and a target date. I ended up adding more input validation here than I originally planned. Every time I thought I'd covered the edge cases, I'd find another one, a negative price, a date typed as `01-01-2027` instead of `2027-01-01`. The function now raises a `ValueError` with a specific message for each of these, rather than letting bad data quietly corrupt the saved file.

`log_milestone()` records progress against one of six stages: Land Acquisition, Foundation, Superstructure, Roofing, Finishes, and Handover. Each milestone entry has a `verified` boolean that marks whether the percentage was independently confirmed or just self-reported by the developer. In the current version you set this manually, but it's the field that matters most if this tool ever connects to a real verification layer.

`calculate_roi()` takes an entry price, annual appreciation rate, holding period in years, and rental yield, and returns a full breakdown — projected value, capital gain, rental income, total return, and both total and annualised ROI. This function caused the most trouble in testing. Python's floating-point arithmetic kept producing values like `1200000.0000000002` instead of clean numbers, which made my early `==` comparisons fail unpredictably. I had to look up `pytest.approx` specifically to fix this, and I now use it across all the ROI tests.

`flag_delays()` computes what percentage of the total project timeline has elapsed, compares it to the average milestone completion, and returns a status: GREEN if progress is on track, AMBER if it's 5–15% behind, RED if it's more than 15% behind or the target date has already passed.

`generate_report()` writes a CSV with one row per project, pulling in the delay status and a fresh ROI calculation for each.

---

## Design Choices

**JSON over SQLite:** A JSON file requires no setup and lives right in the project folder. For a single-user local tool this was the right call. SQLite would make more sense if multiple users were writing to the same data at the same time, but that's not the use case here.

**CLI over a web interface:** The CS50P course is about Python fundamentals, and I wanted the logic clean and independently testable before putting any UI on top of it. Every function in `project.py` can be imported and called directly, which makes testing straightforward and keeps the door open for wiring this into a web backend later.

**`rich` as an optional dependency:** The `rich` library gives the terminal output colour, tables, and panels, which makes the tool much more readable in practice. But it's wrapped in a `try/except` at import time so the program still runs in plain text if `rich` isn't installed — useful for environments where you can't control what's available.

---

*Ann Njeri Mucheke · BSc Electrical & Electronics Engineering, DeKUT · Nairobi, Kenya · 2026*