from __future__ import annotations

from collections import Counter
from datetime import date, datetime, time, timedelta
import random
import sqlite3
from pathlib import Path

from clinic_nl2sql.constants import DATABASE_PATH
from clinic_nl2sql.logging_utils import configure_logging


RANDOM_SEED = 42
DOCTOR_NAMES = [
    ("Amelia Shah", "Dermatology"),
    ("Noah Bennett", "Dermatology"),
    ("Sophia Clarke", "Dermatology"),
    ("Ethan Morris", "Cardiology"),
    ("Olivia Patel", "Cardiology"),
    ("Liam Foster", "Cardiology"),
    ("Ava Reynolds", "Orthopedics"),
    ("Mason Hughes", "Orthopedics"),
    ("Isabella Torres", "Orthopedics"),
    ("Lucas Perry", "General"),
    ("Mia Sanders", "General"),
    ("Elijah Brooks", "General"),
    ("Charlotte Nguyen", "Pediatrics"),
    ("James Cooper", "Pediatrics"),
    ("Harper Kelly", "Pediatrics"),
]
FIRST_NAMES = [
    "Aarav", "Aisha", "Anaya", "Arjun", "Ava", "Benjamin", "Charlotte", "Daniel",
    "Diya", "Eleanor", "Elijah", "Emma", "Ethan", "Grace", "Henry", "Isha",
    "Isabella", "Jack", "James", "Kavya", "Liam", "Lucas", "Maya", "Mia",
    "Nora", "Noah", "Olivia", "Priya", "Riya", "Ryan", "Samuel", "Sarah",
    "Sophia", "Vihaan", "William", "Zara",
]
LAST_NAMES = [
    "Anderson", "Baker", "Carter", "Clark", "Davis", "Evans", "Foster", "Garcia",
    "Hall", "Harris", "Hughes", "Jackson", "Johnson", "Kelly", "Khan", "Lewis",
    "Lopez", "Martin", "Mitchell", "Moore", "Nguyen", "Patel", "Perry", "Reed",
    "Reynolds", "Roberts", "Shah", "Singh", "Taylor", "Thomas", "Torres", "Walker",
    "White", "Williams", "Wilson", "Young",
]
CITIES = [
    "New York", "Chicago", "Austin", "Seattle", "Boston",
    "Denver", "Phoenix", "San Diego", "Atlanta", "Dallas",
]
NOTES = [
    "Follow-up visit recommended.",
    "Patient reported improvement.",
    "Need lab review at next visit.",
    "Prescribed medication and rest.",
    "Discussed lifestyle adjustments.",
    "Requires imaging before next consultation.",
]
TREATMENT_CATALOG = {
    "Dermatology": [
        ("Skin Consultation", (75, 220), (20, 45)),
        ("Allergy Treatment", (120, 450), (25, 60)),
        ("Laser Procedure", (500, 1800), (30, 90)),
    ],
    "Cardiology": [
        ("Cardiac Review", (150, 500), (30, 60)),
        ("Stress Test", (400, 1200), (45, 90)),
        ("ECG Monitoring", (180, 650), (20, 40)),
    ],
    "Orthopedics": [
        ("Joint Assessment", (130, 400), (25, 50)),
        ("Physical Therapy Session", (90, 260), (30, 60)),
        ("Minor Fracture Care", (500, 2200), (45, 100)),
    ],
    "General": [
        ("General Checkup", (50, 180), (15, 30)),
        ("Vaccination Visit", (60, 220), (10, 25)),
        ("Preventive Screening", (100, 300), (20, 40)),
    ],
    "Pediatrics": [
        ("Child Wellness Exam", (70, 210), (20, 35)),
        ("Growth Assessment", (90, 240), (20, 40)),
        ("Pediatric Follow-up", (80, 200), (15, 30)),
    ],
}


def random_date_within_last_year(rng: random.Random) -> date:
    today = date.today()
    offset_days = rng.randint(0, 364)
    return today - timedelta(days=offset_days)


def random_datetime_within_last_year(rng: random.Random) -> datetime:
    base_date = random_date_within_last_year(rng)
    hour = rng.randint(8, 17)
    minute = rng.choice([0, 15, 30, 45])
    return datetime.combine(base_date, time(hour=hour, minute=minute))


def maybe_null(rng: random.Random, value: str, probability: float) -> str | None:
    return None if rng.random() < probability else value


def create_schema(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );
        """
    )


def seed_doctors(cursor: sqlite3.Cursor, rng: random.Random) -> list[dict[str, str]]:
    doctors: list[dict[str, str]] = []
    for name, specialization in DOCTOR_NAMES:
        department = specialization
        phone = f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}"
        cursor.execute(
            """
            INSERT INTO doctors (name, specialization, department, phone)
            VALUES (?, ?, ?, ?)
            """,
            (name, specialization, department, phone),
        )
        doctors.append(
            {
                "id": cursor.lastrowid,
                "name": name,
                "specialization": specialization,
                "department": department,
            }
        )
    return doctors


def seed_patients(cursor: sqlite3.Cursor, rng: random.Random) -> list[dict[str, str]]:
    patients: list[dict[str, str]] = []
    for _ in range(200):
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)
        email = maybe_null(
            rng,
            f"{first_name.lower()}.{last_name.lower()}{rng.randint(1, 99)}@example.com",
            0.16,
        )
        phone = maybe_null(
            rng,
            f"+1-555-{rng.randint(100, 999)}-{rng.randint(1000, 9999)}",
            0.12,
        )
        dob = date.today() - timedelta(days=rng.randint(18 * 365, 85 * 365))
        gender = rng.choice(["M", "F"])
        city = rng.choice(CITIES)
        registered_date = random_date_within_last_year(rng)
        cursor.execute(
            """
            INSERT INTO patients
            (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                email,
                phone,
                dob.isoformat(),
                gender,
                city,
                registered_date.isoformat(),
            ),
        )
        patients.append(
            {
                "id": cursor.lastrowid,
                "first_name": first_name,
                "last_name": last_name,
                "city": city,
            }
        )
    return patients


def seed_appointments(
    cursor: sqlite3.Cursor,
    rng: random.Random,
    patients: list[dict[str, str]],
    doctors: list[dict[str, str]],
) -> list[dict[str, object]]:
    hot_patient_ids = [patient["id"] for patient in patients[:40]]
    patient_weights = [6 if patient["id"] in hot_patient_ids else 1 for patient in patients]
    doctor_weights = [10, 9, 8, 10, 9, 7, 8, 7, 6, 9, 8, 6, 7, 6, 5]
    status_choices = ["Completed", "Scheduled", "Cancelled", "No-Show"]
    status_weights = [0.72, 0.12, 0.10, 0.06]

    appointments: list[dict[str, object]] = []
    for _ in range(500):
        patient = rng.choices(patients, weights=patient_weights, k=1)[0]
        doctor = rng.choices(doctors, weights=doctor_weights, k=1)[0]
        appointment_date = random_datetime_within_last_year(rng)
        status = rng.choices(status_choices, weights=status_weights, k=1)[0]
        notes = maybe_null(rng, rng.choice(NOTES), 0.35)

        cursor.execute(
            """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                patient["id"],
                doctor["id"],
                appointment_date.isoformat(sep=" "),
                status,
                notes,
            ),
        )

        appointments.append(
            {
                "id": cursor.lastrowid,
                "patient_id": patient["id"],
                "doctor_id": doctor["id"],
                "specialization": doctor["specialization"],
                "appointment_date": appointment_date,
                "status": status,
            }
        )
    return appointments


def seed_treatments(
    cursor: sqlite3.Cursor,
    rng: random.Random,
    appointments: list[dict[str, object]],
) -> list[dict[str, object]]:
    completed_appointments = [appointment for appointment in appointments if appointment["status"] == "Completed"]
    chosen_appointments = rng.sample(completed_appointments, 350)
    treatments: list[dict[str, object]] = []
    for appointment in chosen_appointments:
        treatment_name, cost_range, duration_range = rng.choice(
            TREATMENT_CATALOG[str(appointment["specialization"])]
        )
        cost = round(rng.uniform(*cost_range), 2)
        duration_minutes = rng.randint(*duration_range)
        cursor.execute(
            """
            INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
            VALUES (?, ?, ?, ?)
            """,
            (appointment["id"], treatment_name, cost, duration_minutes),
        )
        treatments.append(
            {
                "id": cursor.lastrowid,
                "appointment_id": appointment["id"],
                "patient_id": appointment["patient_id"],
                "appointment_date": appointment["appointment_date"],
                "cost": cost,
            }
        )
    return treatments


def seed_invoices(
    cursor: sqlite3.Cursor,
    rng: random.Random,
    treatments: list[dict[str, object]],
    appointments: list[dict[str, object]],
) -> list[dict[str, object]]:
    appointment_lookup = {appointment["id"]: appointment for appointment in appointments}
    treatment_groups: dict[int, list[dict[str, object]]] = {}
    for treatment in treatments:
        treatment_groups.setdefault(int(treatment["appointment_id"]), []).append(treatment)

    invoice_candidates = list(treatment_groups.items())
    extra_candidates = [appointment for appointment in appointments if appointment["status"] == "Completed"]
    invoices: list[dict[str, object]] = []
    invoice_status_choices = ["Paid", "Pending", "Overdue"]
    invoice_status_weights = [0.62, 0.23, 0.15]

    while len(invoices) < 300:
        if len(invoices) < len(invoice_candidates):
            appointment_id, grouped_treatments = invoice_candidates[len(invoices)]
            appointment = appointment_lookup[appointment_id]
            base_amount = sum(float(item["cost"]) for item in grouped_treatments)
        else:
            appointment = rng.choice(extra_candidates)
            base_amount = round(rng.uniform(80, 800), 2)

        total_amount = round(min(max(base_amount + rng.uniform(0, 120), 50), 5000), 2)
        status = rng.choices(invoice_status_choices, weights=invoice_status_weights, k=1)[0]
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(total_amount * rng.uniform(0.2, 0.85), 2)
        else:
            paid_amount = round(total_amount * rng.uniform(0.0, 0.35), 2)

        invoice_date = (
            appointment["appointment_date"].date()
            if isinstance(appointment["appointment_date"], datetime)
            else random_date_within_last_year(rng)
        )
        invoice_date = min(invoice_date + timedelta(days=rng.randint(0, 7)), date.today())

        cursor.execute(
            """
            INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                appointment["patient_id"],
                invoice_date.isoformat(),
                total_amount,
                paid_amount,
                status,
            ),
        )

        invoices.append(
            {
                "id": cursor.lastrowid,
                "patient_id": appointment["patient_id"],
                "status": status,
            }
        )

    return invoices


def main() -> None:
    configure_logging()
    rng = random.Random(RANDOM_SEED)

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    create_schema(cursor)
    doctors = seed_doctors(cursor, rng)
    patients = seed_patients(cursor, rng)
    appointments = seed_appointments(cursor, rng, patients, doctors)
    treatments = seed_treatments(cursor, rng, appointments)
    invoices = seed_invoices(cursor, rng, treatments, appointments)

    conn.commit()
    conn.close()

    appointment_status_counts = Counter(item["status"] for item in appointments)
    invoice_status_counts = Counter(item["status"] for item in invoices)

    print(
        "Created "
        f"{len(patients)} patients, "
        f"{len(doctors)} doctors, "
        f"{len(appointments)} appointments, "
        f"{len(treatments)} treatments, "
        f"{len(invoices)} invoices."
    )
    print(f"Appointment statuses: {dict(appointment_status_counts)}")
    print(f"Invoice statuses: {dict(invoice_status_counts)}")
    print(f"Database written to {Path(DATABASE_PATH).resolve()}")


if __name__ == "__main__":
    main()
