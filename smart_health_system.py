"""
================================================================================
 SMART HEALTH INFORMATICS AND PATIENT MANAGEMENT SYSTEM (SHIPMS)
================================================================================
 Project      : CSE Programming Mini Project
 Description  : A console-based Patient Management System that digitizes
                hospital operations — patient registration, doctor records,
                appointment scheduling, medical history / diagnosis tracking,
                prescriptions, billing, and basic health analytics.

 Language     : Python 3
 Storage      : SQLite3 (built-in, no external DB server required)
 Author       : <Your Name Here>

 WHY THIS DESIGN?
 -----------------
 Real hospital information systems store data persistently and relationally
 (patients <-> appointments <-> doctors <-> prescriptions <-> bills). SQLite
 is used here because it ships with Python (no installation needed) but still
 demonstrates genuine relational database concepts (tables, foreign keys,
 joins) — exactly what a "Health Informatics" project is expected to show.
================================================================================
"""

import sqlite3
import datetime
import os
import sys

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hospital.db")


# ============================================================================
# DATABASE LAYER
# ============================================================================
class Database:
    """Handles all direct interaction with the SQLite database."""

    def __init__(self, db_name=DB_NAME):
        self.conn = sqlite3.connect(db_name)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            patient_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            age             INTEGER NOT NULL,
            gender          TEXT NOT NULL,
            phone           TEXT NOT NULL,
            blood_group     TEXT,
            address         TEXT,
            registered_on   TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            specialization  TEXT NOT NULL,
            phone           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      INTEGER NOT NULL,
            doctor_id       INTEGER NOT NULL,
            appt_date       TEXT NOT NULL,
            reason          TEXT,
            status          TEXT DEFAULT 'Scheduled',
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id)
        );

        CREATE TABLE IF NOT EXISTS medical_records (
            record_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      INTEGER NOT NULL,
            doctor_id       INTEGER NOT NULL,
            diagnosis       TEXT NOT NULL,
            prescription    TEXT,
            record_date     TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id)  REFERENCES doctors(doctor_id)
        );

        CREATE TABLE IF NOT EXISTS bills (
            bill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id      INTEGER NOT NULL,
            description     TEXT NOT NULL,
            amount          REAL NOT NULL,
            bill_date       TEXT NOT NULL,
            paid            TEXT DEFAULT 'Unpaid',
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        );
        """)
        self.conn.commit()

    def run(self, query, params=()):
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()


# ============================================================================
# UTILITY HELPERS
# ============================================================================
def today():
    return datetime.date.today().isoformat()


def now_stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def line(char="-", n=70):
    print(char * n)


def pause():
    input("\nPress Enter to continue...")


def get_int(prompt):
    while True:
        val = input(prompt).strip()
        if val.isdigit():
            return int(val)
        print("  Invalid input. Please enter a number.")


def get_float(prompt):
    while True:
        val = input(prompt).strip()
        try:
            return float(val)
        except ValueError:
            print("  Invalid input. Please enter a valid amount.")


def get_nonempty(prompt):
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("  This field cannot be empty.")


# ============================================================================
# CORE MODULE: PATIENT MANAGEMENT
# ============================================================================
class PatientManager:
    def __init__(self, db: Database):
        self.db = db

    def add_patient(self):
        line()
        print("REGISTER NEW PATIENT")
        line()
        name = get_nonempty("Full Name        : ")
        age = get_int("Age              : ")
        gender = get_nonempty("Gender (M/F/O)   : ")
        phone = get_nonempty("Phone Number     : ")
        blood = input("Blood Group      : ").strip() or "Not Recorded"
        address = input("Address          : ").strip() or "Not Recorded"

        self.db.run(
            """INSERT INTO patients (name, age, gender, phone, blood_group, address, registered_on)
               VALUES (?,?,?,?,?,?,?)""",
            (name, age, gender, phone, blood, address, today()),
        )
        pid = self.db.cursor.lastrowid
        print(f"\n✔ Patient registered successfully. Patient ID = {pid}")

    def view_all(self):
        rows = self.db.fetch_all("SELECT * FROM patients ORDER BY patient_id")
        line()
        print("ALL REGISTERED PATIENTS")
        line()
        if not rows:
            print("No patients found.")
            return
        print(f"{'ID':<4}{'Name':<20}{'Age':<5}{'Gender':<8}{'Phone':<14}{'Blood':<8}{'Since'}")
        line()
        for r in rows:
            print(f"{r[0]:<4}{r[1]:<20}{r[2]:<5}{r[3]:<8}{r[4]:<14}{r[5]:<8}{r[7]}")

    def search_patient(self):
        term = get_nonempty("Enter Patient ID or Name to search: ")
        if term.isdigit():
            rows = self.db.fetch_all("SELECT * FROM patients WHERE patient_id=?", (term,))
        else:
            rows = self.db.fetch_all("SELECT * FROM patients WHERE name LIKE ?", (f"%{term}%",))
        line()
        if not rows:
            print("No matching patient found.")
        for r in rows:
            print(f"ID:{r[0]}  Name:{r[1]}  Age:{r[2]}  Gender:{r[3]}  Phone:{r[4]}  "
                  f"Blood:{r[5]}  Address:{r[6]}  Registered:{r[7]}")

    def delete_patient(self):
        pid = get_int("Enter Patient ID to remove: ")
        self.db.run("DELETE FROM patients WHERE patient_id=?", (pid,))
        print("✔ Patient record removed (if it existed).")

    def patient_history(self, patient_id=None):
        if patient_id is None:
            patient_id = get_int("Enter Patient ID: ")
        line()
        print(f"MEDICAL HISTORY — Patient ID {patient_id}")
        line()
        rows = self.db.fetch_all(
            """SELECT mr.record_date, d.name, mr.diagnosis, mr.prescription
               FROM medical_records mr
               JOIN doctors d ON mr.doctor_id = d.doctor_id
               WHERE mr.patient_id=? ORDER BY mr.record_date""",
            (patient_id,),
        )
        if not rows:
            print("No medical records found for this patient.")
            return
        for r in rows:
            print(f"Date: {r[0]} | Doctor: {r[1]}")
            print(f"  Diagnosis    : {r[2]}")
            print(f"  Prescription : {r[3]}")
            line(".")


# ============================================================================
# CORE MODULE: DOCTOR MANAGEMENT
# ============================================================================
class DoctorManager:
    def __init__(self, db: Database):
        self.db = db

    def add_doctor(self):
        line()
        print("ADD NEW DOCTOR")
        line()
        name = get_nonempty("Doctor Name      : ")
        spec = get_nonempty("Specialization   : ")
        phone = get_nonempty("Phone Number     : ")
        self.db.run(
            "INSERT INTO doctors (name, specialization, phone) VALUES (?,?,?)",
            (name, spec, phone),
        )
        did = self.db.cursor.lastrowid
        print(f"\n✔ Doctor added successfully. Doctor ID = {did}")

    def view_all(self):
        rows = self.db.fetch_all("SELECT * FROM doctors ORDER BY doctor_id")
        line()
        print("ALL DOCTORS")
        line()
        if not rows:
            print("No doctors found.")
            return
        print(f"{'ID':<4}{'Name':<20}{'Specialization':<22}{'Phone'}")
        line()
        for r in rows:
            print(f"{r[0]:<4}{r[1]:<20}{r[2]:<22}{r[3]}")


# ============================================================================
# CORE MODULE: APPOINTMENT SCHEDULING
# ============================================================================
class AppointmentManager:
    def __init__(self, db: Database):
        self.db = db

    def book(self):
        line()
        print("BOOK APPOINTMENT")
        line()
        pid = get_int("Patient ID       : ")
        if not self.db.fetch_one("SELECT 1 FROM patients WHERE patient_id=?", (pid,)):
            print("✘ No such patient. Register the patient first.")
            return
        did = get_int("Doctor ID        : ")
        if not self.db.fetch_one("SELECT 1 FROM doctors WHERE doctor_id=?", (did,)):
            print("✘ No such doctor.")
            return
        date = input("Appointment Date (YYYY-MM-DD) [today]: ").strip() or today()
        reason = get_nonempty("Reason for Visit : ")

        self.db.run(
            """INSERT INTO appointments (patient_id, doctor_id, appt_date, reason, status)
               VALUES (?,?,?,?, 'Scheduled')""",
            (pid, did, date, reason),
        )
        aid = self.db.cursor.lastrowid
        print(f"\n✔ Appointment booked. Appointment ID = {aid}")

    def view_all(self):
        rows = self.db.fetch_all(
            """SELECT a.appointment_id, p.name, d.name, a.appt_date, a.reason, a.status
               FROM appointments a
               JOIN patients p ON a.patient_id = p.patient_id
               JOIN doctors d ON a.doctor_id = d.doctor_id
               ORDER BY a.appt_date"""
        )
        line()
        print("ALL APPOINTMENTS")
        line()
        if not rows:
            print("No appointments scheduled.")
            return
        print(f"{'ID':<4}{'Patient':<16}{'Doctor':<20}{'Date':<12}{'Status':<12}{'Reason'}")
        line()
        for r in rows:
            print(f"{r[0]:<4}{r[1]:<16}{r[2]:<20}{r[3]:<12}{r[5]:<12}{r[4]}")

    def complete_appointment(self):
        """Marks an appointment done AND records diagnosis/prescription in one flow."""
        aid = get_int("Enter Appointment ID to complete: ")
        appt = self.db.fetch_one(
            "SELECT patient_id, doctor_id FROM appointments WHERE appointment_id=?", (aid,)
        )
        if not appt:
            print("✘ No such appointment.")
            return
        pid, did = appt
        diagnosis = get_nonempty("Diagnosis        : ")
        prescription = input("Prescription     : ").strip() or "None"

        self.db.run("UPDATE appointments SET status='Completed' WHERE appointment_id=?", (aid,))
        self.db.run(
            """INSERT INTO medical_records (patient_id, doctor_id, diagnosis, prescription, record_date)
               VALUES (?,?,?,?,?)""",
            (pid, did, diagnosis, prescription, today()),
        )
        print("\n✔ Appointment marked completed and medical record saved.")


# ============================================================================
# CORE MODULE: BILLING
# ============================================================================
class BillingManager:
    def __init__(self, db: Database):
        self.db = db

    def generate_bill(self):
        line()
        print("GENERATE BILL")
        line()
        pid = get_int("Patient ID       : ")
        if not self.db.fetch_one("SELECT 1 FROM patients WHERE patient_id=?", (pid,)):
            print("✘ No such patient.")
            return
        desc = get_nonempty("Description (e.g. Consultation, Lab Test): ")
        amount = get_float("Amount (Rs.)     : ")
        self.db.run(
            "INSERT INTO bills (patient_id, description, amount, bill_date, paid) VALUES (?,?,?,?, 'Unpaid')",
            (pid, desc, amount, today()),
        )
        bid = self.db.cursor.lastrowid
        print(f"\n✔ Bill generated. Bill ID = {bid}, Amount = Rs.{amount:.2f}")

    def mark_paid(self):
        bid = get_int("Enter Bill ID to mark as paid: ")
        self.db.run("UPDATE bills SET paid='Paid' WHERE bill_id=?", (bid,))
        print("✔ Bill status updated to Paid (if it existed).")

    def view_all(self):
        rows = self.db.fetch_all(
            """SELECT b.bill_id, p.name, b.description, b.amount, b.bill_date, b.paid
               FROM bills b JOIN patients p ON b.patient_id = p.patient_id
               ORDER BY b.bill_date"""
        )
        line()
        print("ALL BILLS")
        line()
        if not rows:
            print("No bills found.")
            return
        total_due = 0
        print(f"{'ID':<4}{'Patient':<16}{'Description':<22}{'Amount':<10}{'Date':<12}{'Status'}")
        line()
        for r in rows:
            print(f"{r[0]:<4}{r[1]:<16}{r[2]:<22}{r[3]:<10.2f}{r[4]:<12}{r[5]}")
            if r[5] == "Unpaid":
                total_due += r[3]
        line()
        print(f"Total Outstanding (Unpaid) Amount: Rs.{total_due:.2f}")


# ============================================================================
# CORE MODULE: HEALTH ANALYTICS / REPORTS
# (adds genuine "informatics" value — simple statistics over stored data)
# ============================================================================
class ReportManager:
    def __init__(self, db: Database):
        self.db = db

    def dashboard(self):
        line("=")
        print("HOSPITAL ANALYTICS DASHBOARD")
        line("=")

        total_patients = self.db.fetch_one("SELECT COUNT(*) FROM patients")[0]
        total_doctors = self.db.fetch_one("SELECT COUNT(*) FROM doctors")[0]
        total_appts = self.db.fetch_one("SELECT COUNT(*) FROM appointments")[0]
        completed = self.db.fetch_one(
            "SELECT COUNT(*) FROM appointments WHERE status='Completed'"
        )[0]
        pending = total_appts - completed
        revenue = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount),0) FROM bills WHERE paid='Paid'"
        )[0]
        due = self.db.fetch_one(
            "SELECT COALESCE(SUM(amount),0) FROM bills WHERE paid='Unpaid'"
        )[0]

        print(f"Total Registered Patients   : {total_patients}")
        print(f"Total Doctors on Staff      : {total_doctors}")
        print(f"Total Appointments          : {total_appts}  "
              f"(Completed: {completed}, Pending: {pending})")
        print(f"Revenue Collected           : Rs.{revenue:.2f}")
        print(f"Outstanding Dues            : Rs.{due:.2f}")

        # Most common diagnosis -> demonstrates GROUP BY / aggregate query
        top = self.db.fetch_all(
            """SELECT diagnosis, COUNT(*) c FROM medical_records
               GROUP BY diagnosis ORDER BY c DESC LIMIT 3"""
        )
        if top:
            print("\nTop Diagnoses Recorded:")
            for d, c in top:
                print(f"  - {d}: {c} case(s)")

        # Doctor with most appointments
        busiest = self.db.fetch_one(
            """SELECT d.name, COUNT(*) c FROM appointments a
               JOIN doctors d ON a.doctor_id = d.doctor_id
               GROUP BY d.name ORDER BY c DESC LIMIT 1"""
        )
        if busiest:
            print(f"\nBusiest Doctor              : {busiest[0]} ({busiest[1]} appointment(s))")
        line("=")


# ============================================================================
# APPLICATION / MENU LAYER
# ============================================================================
class HospitalApp:
    def __init__(self):
        self.db = Database()
        self.patients = PatientManager(self.db)
        self.doctors = DoctorManager(self.db)
        self.appts = AppointmentManager(self.db)
        self.billing = BillingManager(self.db)
        self.reports = ReportManager(self.db)

    def banner(self):
        os.system("cls" if os.name == "nt" else "clear")
        line("=")
        print("   SMART HEALTH INFORMATICS AND PATIENT MANAGEMENT SYSTEM")
        print(f"   {now_stamp()}")
        line("=")

    def main_menu(self):
        while True:
            self.banner()
            print("""
 1. Patient Management
 2. Doctor Management
 3. Appointment Scheduling
 4. Billing
 5. Analytics Dashboard
 0. Exit
""")
            choice = input("Select an option: ").strip()
            if choice == "1":
                self.patient_menu()
            elif choice == "2":
                self.doctor_menu()
            elif choice == "3":
                self.appointment_menu()
            elif choice == "4":
                self.billing_menu()
            elif choice == "5":
                self.reports.dashboard()
                pause()
            elif choice == "0":
                print("\nThank you for using SHIPMS. Goodbye!")
                self.db.close()
                sys.exit(0)
            else:
                print("Invalid option.")
                pause()

    def patient_menu(self):
        while True:
            self.banner()
            print("""
 PATIENT MANAGEMENT
 1. Register New Patient
 2. View All Patients
 3. Search Patient
 4. View Patient Medical History
 5. Delete Patient
 0. Back to Main Menu
""")
            c = input("Select an option: ").strip()
            if c == "1": self.patients.add_patient()
            elif c == "2": self.patients.view_all()
            elif c == "3": self.patients.search_patient()
            elif c == "4": self.patients.patient_history()
            elif c == "5": self.patients.delete_patient()
            elif c == "0": return
            else: print("Invalid option.")
            pause()

    def doctor_menu(self):
        while True:
            self.banner()
            print("""
 DOCTOR MANAGEMENT
 1. Add New Doctor
 2. View All Doctors
 0. Back to Main Menu
""")
            c = input("Select an option: ").strip()
            if c == "1": self.doctors.add_doctor()
            elif c == "2": self.doctors.view_all()
            elif c == "0": return
            else: print("Invalid option.")
            pause()

    def appointment_menu(self):
        while True:
            self.banner()
            print("""
 APPOINTMENT SCHEDULING
 1. Book Appointment
 2. View All Appointments
 3. Complete Appointment (Add Diagnosis + Prescription)
 0. Back to Main Menu
""")
            c = input("Select an option: ").strip()
            if c == "1": self.appts.book()
            elif c == "2": self.appts.view_all()
            elif c == "3": self.appts.complete_appointment()
            elif c == "0": return
            else: print("Invalid option.")
            pause()

    def billing_menu(self):
        while True:
            self.banner()
            print("""
 BILLING
 1. Generate Bill
 2. Mark Bill as Paid
 3. View All Bills
 0. Back to Main Menu
""")
            c = input("Select an option: ").strip()
            if c == "1": self.billing.generate_bill()
            elif c == "2": self.billing.mark_paid()
            elif c == "3": self.billing.view_all()
            elif c == "0": return
            else: print("Invalid option.")
            pause()


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    app = HospitalApp()
    app.main_menu()
