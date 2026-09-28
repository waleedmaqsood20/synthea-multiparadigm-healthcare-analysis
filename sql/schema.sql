-- schema.sql
--
-- Relational schema for the eight Synthea CSV tables used in this project
-- (see data/README.md for how to obtain them). This mirrors the standard
-- Synthea CSV export column layout, as reflected in the SQLite database
-- generated from the 5,000-patient subset during this project.
--
-- To build a local SQLite database from data/subset/*.csv:
--   sqlite3 synthea.db
--   .mode csv
--   .import data/subset/patients.csv patients        (repeat --skip 1 header row per file, or use .import --csv --skip 1)
-- or load each CSV with pandas.to_sql() -- see README.md "Reproducibility".

CREATE TABLE IF NOT EXISTS patients (
    Id                    TEXT PRIMARY KEY,
    BIRTHDATE             TEXT,
    DEATHDATE             TEXT,
    SSN                   TEXT,
    DRIVERS               TEXT,
    PASSPORT              TEXT,
    PREFIX                TEXT,
    FIRST                 TEXT,
    LAST                  TEXT,
    SUFFIX                TEXT,
    MAIDEN                TEXT,
    MARITAL               TEXT,
    RACE                  TEXT,
    ETHNICITY             TEXT,
    GENDER                TEXT,
    BIRTHPLACE            TEXT,
    ADDRESS               TEXT,
    CITY                  TEXT,
    STATE                 TEXT,
    COUNTY                TEXT,
    ZIP                   INTEGER,
    LAT                   REAL,
    LON                   REAL,
    HEALTHCARE_EXPENSES   REAL,
    HEALTHCARE_COVERAGE   REAL,
    INCOME                INTEGER
);

CREATE TABLE IF NOT EXISTS organizations (
    Id            TEXT PRIMARY KEY,
    NAME          TEXT,
    ADDRESS       TEXT,
    CITY          TEXT,
    STATE         TEXT,
    ZIP           INTEGER,
    LAT           REAL,
    LON           REAL,
    PHONE         TEXT,
    REVENUE       REAL,
    UTILIZATION   INTEGER
);

CREATE TABLE IF NOT EXISTS providers (
    Id            TEXT PRIMARY KEY,
    ORGANIZATION  TEXT REFERENCES organizations(Id),
    NAME          TEXT,
    GENDER        TEXT,
    SPECIALITY    TEXT,
    ADDRESS       TEXT,
    CITY          TEXT,
    STATE         TEXT,
    ZIP           INTEGER,
    LAT           REAL,
    LON           REAL,
    UTILIZATION   INTEGER
);

CREATE TABLE IF NOT EXISTS encounters (
    Id                    TEXT PRIMARY KEY,
    START                 TEXT,
    STOP                  TEXT,
    PATIENT               TEXT REFERENCES patients(Id),
    ORGANIZATION          TEXT REFERENCES organizations(Id),
    PROVIDER              TEXT REFERENCES providers(Id),
    PAYER                 TEXT,
    ENCOUNTERCLASS        TEXT,
    CODE                  INTEGER,
    DESCRIPTION           TEXT,
    BASE_ENCOUNTER_COST   REAL,
    TOTAL_CLAIM_COST      REAL,
    PAYER_COVERAGE        REAL,
    REASONCODE            REAL,
    REASONDESCRIPTION     TEXT
);

CREATE TABLE IF NOT EXISTS conditions (
    START         TEXT,
    STOP          TEXT,
    PATIENT       TEXT REFERENCES patients(Id),
    ENCOUNTER     TEXT REFERENCES encounters(Id),
    CODE          INTEGER,
    DESCRIPTION   TEXT
);

CREATE TABLE IF NOT EXISTS medications (
    START               TEXT,
    STOP                TEXT,
    PATIENT             TEXT REFERENCES patients(Id),
    PAYER               TEXT,
    ENCOUNTER           TEXT REFERENCES encounters(Id),
    CODE                INTEGER,
    DESCRIPTION         TEXT,
    BASE_COST           REAL,
    PAYER_COVERAGE      REAL,
    DISPENSES           INTEGER,
    TOTALCOST           REAL,
    REASONCODE          REAL,
    REASONDESCRIPTION   TEXT
);

CREATE TABLE IF NOT EXISTS procedures (
    START               TEXT,
    STOP                TEXT,
    PATIENT             TEXT REFERENCES patients(Id),
    ENCOUNTER           TEXT REFERENCES encounters(Id),
    CODE                INTEGER,
    DESCRIPTION         TEXT,
    BASE_COST           REAL,
    REASONCODE          REAL,
    REASONDESCRIPTION   TEXT
);

CREATE TABLE IF NOT EXISTS immunizations (
    DATE          TEXT,
    PATIENT       TEXT REFERENCES patients(Id),
    ENCOUNTER     TEXT REFERENCES encounters(Id),
    CODE          INTEGER,
    DESCRIPTION   TEXT,
    BASE_COST     REAL
);

CREATE INDEX IF NOT EXISTS idx_conditions_patient   ON conditions(PATIENT);
CREATE INDEX IF NOT EXISTS idx_conditions_encounter  ON conditions(ENCOUNTER);
CREATE INDEX IF NOT EXISTS idx_medications_patient   ON medications(PATIENT);
CREATE INDEX IF NOT EXISTS idx_medications_encounter ON medications(ENCOUNTER);
CREATE INDEX IF NOT EXISTS idx_encounters_patient    ON encounters(PATIENT);
