#!/usr/bin/env python3
"""Generate docker/mysql/03-seed-100.sql with 100 rows per table."""
import random
from datetime import date, datetime, timedelta

OUTPUT = "docker/mysql/03-seed-100.sql"

DEPARTMENT_NAMES = [
    "Cardiology", "ER", "Surgery", "Pediatrics", "Radiology", "Neurology",
    "Orthopedics", "ICU", "Oncology", "Gastroenterology", "Pulmonology",
    "Nephrology", "Endocrinology", "Rheumatology", "Dermatology", "Urology",
    "Ophthalmology", "ENT", "Psychiatry", "Obstetrics", "Gynecology",
    "Hematology", "Infectious Disease", "Palliative Care", "Rehabilitation",
    "Pathology", "Anesthesiology", "Emergency Medicine", "Family Medicine",
    "Internal Medicine", "Neonatology", "Geriatrics", "Allergy", "Immunology",
]
# Pad to 100 with "Department N"
while len(DEPARTMENT_NAMES) < 100:
    DEPARTMENT_NAMES.append(f"Department {len(DEPARTMENT_NAMES) + 1}")

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
NOTE_SNIPPETS = ["Routine checkup", "Follow-up", "Consultation", "Procedure", "Emergency", "Triage", "Discharge", "Admission", None]

def random_date(start: date, end: date) -> date:
    d = start + timedelta(days=random.randint(0, (end - start).days))
    return d

def escape_sql(s):
    if s is None:
        return "NULL"
    return "'" + str(s).replace("\\", "\\\\").replace("'", "''") + "'"

def main():
    random.seed(42)
    lines = [
        "-- Generated: 100 rows per table. Run after 01-init.sql (clears initial seed, inserts 100 each).",
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

    # Departments
    lines.append("INSERT INTO departments (name) VALUES")
    values = [f"  ({escape_sql(n)})" for n in DEPARTMENT_NAMES[:100]]
    lines.append(",\n".join(values) + ";")
    lines.append("")

    # Patients: 100 with first_name, last_name, date_of_birth
    lines.append("INSERT INTO patients (first_name, last_name, date_of_birth) VALUES")
    start_dob = date(1940, 1, 1)
    end_dob = date(2010, 12, 31)
    pvals = []
    for i in range(100):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        dob = random_date(start_dob, end_dob)
        pvals.append(f"  ({escape_sql(fn)}, {escape_sql(ln)}, {escape_sql(dob)})")
    lines.append(",\n".join(pvals) + ";")
    lines.append("")

    # Appointments: 100, patient_id 1-100, department_id 1-100, scheduled_at in 2025, status
    lines.append("INSERT INTO appointments (patient_id, department_id, scheduled_at, status) VALUES")
    base = datetime(2025, 1, 1)
    avals = []
    for i in range(100):
        pid = (i % 100) + 1
        did = (i % 100) + 1
        dt = base + timedelta(days=random.randint(0, 90), hours=random.randint(8, 16), minutes=random.choice([0, 15, 30, 45]))
        st = random.choice(STATUSES)
        avals.append(f"  ({pid}, {did}, {escape_sql(dt)}, {escape_sql(st)})")
    lines.append(",\n".join(avals) + ";")
    lines.append("")

    # Visits: 100, patient_id 1-100, department_id 1-100, visit_date, notes
    lines.append("INSERT INTO visits (patient_id, department_id, visit_date, notes) VALUES")
    start_visit = date(2024, 6, 1)
    end_visit = date(2025, 2, 28)
    vvals = []
    for i in range(100):
        pid = (i % 100) + 1
        did = (i % 100) + 1
        vd = random_date(start_visit, end_visit)
        note = random.choice(NOTE_SNIPPETS)
        vvals.append(f"  ({pid}, {did}, {escape_sql(vd)}, {escape_sql(note)})")
    lines.append(",\n".join(vvals) + ";")
    lines.append("")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUTPUT}")

if __name__ == "__main__":
    main()
