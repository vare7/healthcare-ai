#!/usr/bin/env python3
"""Generate docker/mysql/03-seed-100.sql with realistic healthcare seed data.

Produces ~600-700 visits with volume varying by department traffic tier,
spanning June 2024 through Feb 24 2026.
"""
import random
from datetime import date, datetime, timedelta

OUTPUT = "docker/mysql/03-seed-100.sql"

# ---------------------------------------------------------------------------
# Departments (34 named) grouped by realistic hospital traffic volume
# ---------------------------------------------------------------------------
HIGH_TRAFFIC = [
    "ER", "Emergency Medicine", "Internal Medicine", "Family Medicine",
    "Cardiology", "Pediatrics", "Surgery",
]
MEDIUM_TRAFFIC = [
    "Orthopedics", "Neurology", "Oncology", "Gastroenterology",
    "Pulmonology", "Obstetrics", "Gynecology", "ICU", "Psychiatry",
    "Radiology", "Dermatology",
]
LOW_TRAFFIC = [
    "Nephrology", "Endocrinology", "Rheumatology", "Urology",
    "Ophthalmology", "ENT", "Hematology", "Infectious Disease",
    "Palliative Care", "Rehabilitation", "Pathology", "Anesthesiology",
    "Neonatology", "Geriatrics", "Allergy", "Immunology",
]

DEPARTMENT_NAMES = HIGH_TRAFFIC + MEDIUM_TRAFFIC + LOW_TRAFFIC
NUM_DEPARTMENTS = len(DEPARTMENT_NAMES)  # 34

VISIT_RANGE = {
    "high": (30, 50),
    "medium": (15, 25),
    "low": (5, 12),
}

DEPT_TIER = {}
for d in HIGH_TRAFFIC:
    DEPT_TIER[d] = "high"
for d in MEDIUM_TRAFFIC:
    DEPT_TIER[d] = "medium"
for d in LOW_TRAFFIC:
    DEPT_TIER[d] = "low"

# ---------------------------------------------------------------------------
# Department-specific visit note pools
# ---------------------------------------------------------------------------
DEPT_NOTES = {
    "ER":                  ["Emergency", "Triage", "Stabilization", "Trauma assessment", None],
    "Emergency Medicine":  ["Emergency", "Triage", "Acute care", "Trauma assessment", None],
    "Internal Medicine":   ["Routine checkup", "Follow-up", "Chronic disease review", "Consultation", None],
    "Family Medicine":     ["Routine checkup", "Follow-up", "Wellness visit", "Consultation", None],
    "Cardiology":          ["Cardiac consult", "Stress test", "ECG review", "Follow-up", "Routine checkup", None],
    "Pediatrics":          ["Well-child visit", "Vaccination", "Follow-up", "Consultation", None],
    "Surgery":             ["Pre-op assessment", "Post-op follow-up", "Procedure", "Consultation", None],
    "Orthopedics":         ["Fracture follow-up", "Joint evaluation", "Post-op follow-up", "Consultation", None],
    "Neurology":           ["Neurological exam", "Follow-up", "EEG review", "Consultation", None],
    "Oncology":            ["Chemotherapy", "Follow-up", "Consultation", "Treatment review", None],
    "Gastroenterology":    ["Endoscopy", "Follow-up", "Consultation", "GI evaluation", None],
    "Pulmonology":         ["Pulmonary function test", "Follow-up", "Consultation", "Sleep study review", None],
    "Obstetrics":          ["Prenatal visit", "Ultrasound", "Follow-up", "Delivery admission", None],
    "Gynecology":          ["Annual exam", "Follow-up", "Consultation", "Procedure", None],
    "ICU":                 ["Critical care", "Monitoring", "Post-surgical", "Stabilization", None],
    "Psychiatry":          ["Psychiatric evaluation", "Follow-up", "Therapy session", "Medication review", None],
    "Radiology":           ["Imaging", "X-ray", "MRI", "CT scan", "Ultrasound", None],
    "Dermatology":         ["Skin exam", "Follow-up", "Biopsy", "Consultation", None],
    "Nephrology":          ["Dialysis", "Follow-up", "Consultation", "Lab review", None],
    "Endocrinology":       ["Diabetes management", "Thyroid follow-up", "Consultation", None],
    "Rheumatology":        ["Joint evaluation", "Follow-up", "Consultation", "Infusion", None],
    "Urology":             ["Consultation", "Follow-up", "Procedure", "Cystoscopy", None],
    "Ophthalmology":       ["Eye exam", "Follow-up", "Consultation", "Procedure", None],
    "ENT":                 ["Hearing test", "Follow-up", "Consultation", "Procedure", None],
    "Hematology":          ["Blood work review", "Transfusion", "Follow-up", "Consultation", None],
    "Infectious Disease":  ["Consultation", "Follow-up", "Treatment review", "Lab review", None],
    "Palliative Care":     ["Symptom management", "Follow-up", "Family meeting", "Consultation", None],
    "Rehabilitation":      ["Physical therapy", "Occupational therapy", "Follow-up", "Assessment", None],
    "Pathology":           ["Biopsy review", "Lab consultation", "Specimen analysis", None],
    "Anesthesiology":      ["Pre-op evaluation", "Pain management", "Consultation", None],
    "Neonatology":         ["NICU admission", "Follow-up", "Monitoring", "Discharge", None],
    "Geriatrics":          ["Geriatric assessment", "Follow-up", "Medication review", "Consultation", None],
    "Allergy":             ["Allergy testing", "Follow-up", "Immunotherapy", "Consultation", None],
    "Immunology":          ["Immune evaluation", "Follow-up", "Infusion", "Consultation", None],
}
DEFAULT_NOTES = ["Routine checkup", "Follow-up", "Consultation", "Procedure", "Admission", "Discharge", None]

# ---------------------------------------------------------------------------
# Patient name pools
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
]
STATUSES = ["scheduled", "completed", "cancelled", "no-show"]

# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
VISIT_START = date(2024, 6, 1)
VISIT_END = date(2026, 2, 24)  # last week relative to Mar 3, 2026

APPT_START = datetime(2025, 1, 1)
APPT_END = datetime(2026, 3, 31)


def random_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_datetime(start: datetime, end: datetime) -> datetime:
    base = start + timedelta(days=random.randint(0, (end - start).days))
    hour = random.randint(7, 17)
    minute = random.choice([0, 15, 30, 45])
    return base.replace(hour=hour, minute=minute, second=0)


def escape_sql(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("\\", "\\\\").replace("'", "''") + "'"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def main():
    random.seed(42)

    lines = [
        "-- Generated seed data: 34 departments, 100 patients, ~150 appointments,",
        "-- ~600-700 visits with realistic per-department volume.",
        "-- Visit dates: 2024-06-01 through 2026-02-24.",
        "-- Run after 01-init.sql (clears initial seed, inserts fresh data).",
        "USE healthcare_db;",
        "",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "TRUNCATE TABLE visits;",
        "TRUNCATE TABLE appointments;",
        "TRUNCATE TABLE patients;",
        "TRUNCATE TABLE departments;",
        "SET FOREIGN_KEY_CHECKS = 1;",
        "",
    ]

    # --- Departments (34) ---
    lines.append("INSERT INTO departments (name) VALUES")
    values = [f"  ({escape_sql(n)})" for n in DEPARTMENT_NAMES]
    lines.append(",\n".join(values) + ";")
    lines.append("")

    dept_id = {name: idx + 1 for idx, name in enumerate(DEPARTMENT_NAMES)}

    # --- Patients (100) ---
    lines.append("INSERT INTO patients (first_name, last_name, date_of_birth) VALUES")
    dob_start, dob_end = date(1940, 1, 1), date(2010, 12, 31)
    pvals = []
    for _ in range(100):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        dob = random_date(dob_start, dob_end)
        pvals.append(f"  ({escape_sql(fn)}, {escape_sql(ln)}, {escape_sql(dob)})")
    lines.append(",\n".join(pvals) + ";")
    lines.append("")

    # --- Visits (~600-700, varied by department tier) ---
    visit_rows = []
    for dept_name in DEPARTMENT_NAMES:
        tier = DEPT_TIER[dept_name]
        lo, hi = VISIT_RANGE[tier]
        count = random.randint(lo, hi)
        notes_pool = DEPT_NOTES.get(dept_name, DEFAULT_NOTES)
        did = dept_id[dept_name]
        for _ in range(count):
            pid = random.randint(1, 100)
            vd = random_date(VISIT_START, VISIT_END)
            note = random.choice(notes_pool)
            visit_rows.append((pid, did, vd, note))

    random.shuffle(visit_rows)

    lines.append("INSERT INTO visits (patient_id, department_id, visit_date, notes) VALUES")
    vvals = [
        f"  ({pid}, {did}, {escape_sql(vd)}, {escape_sql(note)})"
        for pid, did, vd, note in visit_rows
    ]
    lines.append(",\n".join(vvals) + ";")
    lines.append("")

    # --- Appointments (~150) ---
    appt_rows = []
    for _ in range(150):
        pid = random.randint(1, 100)
        did = random.randint(1, NUM_DEPARTMENTS)
        dt = random_datetime(APPT_START, APPT_END)
        if dt > datetime(2026, 3, 3):
            status = "scheduled"
        else:
            status = random.choice(STATUSES)
        appt_rows.append((pid, did, dt, status))

    lines.append("INSERT INTO appointments (patient_id, department_id, scheduled_at, status) VALUES")
    avals = [
        f"  ({pid}, {did}, {escape_sql(dt)}, {escape_sql(st)})"
        for pid, did, dt, st in appt_rows
    ]
    lines.append(",\n".join(avals) + ";")
    lines.append("")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    total_visits = len(visit_rows)
    print(f"Wrote {OUTPUT}")
    print(f"  Departments: {NUM_DEPARTMENTS}")
    print(f"  Patients:    100")
    print(f"  Visits:      {total_visits}")
    print(f"  Appointments: {len(appt_rows)}")


if __name__ == "__main__":
    main()
