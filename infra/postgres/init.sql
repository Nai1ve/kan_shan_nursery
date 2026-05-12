-- Kanshan PostgreSQL initialization
-- This script runs automatically when the postgres container starts for the first time.

CREATE SCHEMA IF NOT EXISTS profile;
CREATE SCHEMA IF NOT EXISTS seed;
CREATE SCHEMA IF NOT EXISTS writing;
CREATE SCHEMA IF NOT EXISTS sprout;
CREATE SCHEMA IF NOT EXISTS feedback;
