-- One-time migration: add department_id to appointments (existing volumes only).
-- New setups already have this in 01-init.sql. Run this if you kept an old volume
-- and did not want to delete it (e.g. to preserve Ollama models).
-- Usage: docker exec -i <mysql_container> mysql -u root -p healthcare_db < docker/mysql/migrate-appointments-department.sql

USE healthcare_db;

ALTER TABLE appointments
  ADD COLUMN department_id INT NULL,
  ADD CONSTRAINT fk_appointments_department
    FOREIGN KEY (department_id) REFERENCES departments(id);

UPDATE appointments SET department_id = 1 WHERE department_id IS NULL;
