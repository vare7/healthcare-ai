-- Create read-only user for the app (no INSERT/UPDATE/DELETE).
-- Runs after 01-init.sql so healthcare_db exists.

CREATE USER IF NOT EXISTS 'readonly_user'@'%' IDENTIFIED BY 'readonly_pass';
GRANT SELECT ON healthcare_db.* TO 'readonly_user'@'%';
FLUSH PRIVILEGES;
