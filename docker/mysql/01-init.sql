-- Seed database for Healthcare AI Assistant (local dev / Docker)
-- Creates healthcare_db with sample tables and read-only user.

CREATE DATABASE IF NOT EXISTS healthcare_db;
USE healthcare_db;

-- Departments (e.g. Cardiology, ER, Surgery)
CREATE TABLE IF NOT EXISTS departments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Patients (minimal PII for demo)
CREATE TABLE IF NOT EXISTS patients (
  id INT PRIMARY KEY AUTO_INCREMENT,
  first_name VARCHAR(80) NOT NULL,
  last_name VARCHAR(80) NOT NULL,
  date_of_birth DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Appointments
CREATE TABLE IF NOT EXISTS appointments (
  id INT PRIMARY KEY AUTO_INCREMENT,
  patient_id INT NOT NULL,
  scheduled_at DATETIME NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (patient_id) REFERENCES patients(id)
);

-- Visits (admissions / encounters by department)
CREATE TABLE IF NOT EXISTS visits (
  id INT PRIMARY KEY AUTO_INCREMENT,
  patient_id INT NOT NULL,
  department_id INT NOT NULL,
  visit_date DATE NOT NULL,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (patient_id) REFERENCES patients(id),
  FOREIGN KEY (department_id) REFERENCES departments(id)
);

-- Seed data
INSERT INTO departments (name) VALUES
  ('Cardiology'),
  ('ER'),
  ('Surgery'),
  ('Pediatrics'),
  ('Radiology');

INSERT INTO patients (first_name, last_name, date_of_birth) VALUES
  ('Jane', 'Doe', '1985-03-15'),
  ('John', 'Smith', '1990-07-22'),
  ('Maria', 'Garcia', '1978-11-08'),
  ('David', 'Lee', '1995-01-30'),
  ('Sarah', 'Wilson', '1982-09-14'),
  ('James', 'Brown', '1988-04-05');

INSERT INTO appointments (patient_id, scheduled_at, status) VALUES
  (1, '2025-03-10 09:00:00', 'completed'),
  (2, '2025-03-11 10:30:00', 'scheduled'),
  (3, '2025-03-12 14:00:00', 'cancelled'),
  (1, '2025-03-15 11:00:00', 'scheduled'),
  (4, '2025-03-16 08:00:00', 'scheduled');

INSERT INTO visits (patient_id, department_id, visit_date, notes) VALUES
  (1, 1, '2025-01-15', 'Routine checkup'),
  (2, 2, '2025-01-16', 'Minor injury'),
  (3, 1, '2025-01-17', 'Follow-up'),
  (1, 2, '2025-01-20', 'Emergency'),
  (4, 3, '2025-01-22', 'Procedure'),
  (5, 2, '2025-01-25', 'Triage'),
  (2, 1, '2025-02-01', 'Cardiac consult'),
  (6, 4, '2025-02-05', 'Pediatric visit');
