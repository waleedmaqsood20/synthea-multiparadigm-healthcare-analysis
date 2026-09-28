-- analysis_queries.sql
--
-- Relational-paradigm implementation of the project's research question:
-- does having a chronic condition change how many distinct medications a
-- patient is on?
--
-- note: I originally ran this SQL ad hoc in a database tool for Assignment 1
-- and never saved it as a script, so I rewrote it here against schema.sql
-- and reran it against the 5,000-patient subset (data/subset/, seed 42) to
-- make sure I still get the same numbers. See results/verified_results.md
-- for the output, and for how the two variants below compare to PySpark.
--
-- Chronic condition definition (project-specific, shared with the MongoDB
-- and PySpark implementations): a condition whose DESCRIPTION contains,
-- case-insensitively, "diabetes", "hypertension", "hyperlipidemia" or
-- "asthma" as a substring (so it also matches e.g. "Prediabetes",
-- "Childhood asthma", "Diabetic retinopathy...").

-- Q0: how many of the 5,000 subset patients have at least one chronic
-- condition, ever, across any encounter?
WITH chronic_patients AS (
    SELECT DISTINCT PATIENT
    FROM conditions
    WHERE LOWER(DESCRIPTION) LIKE '%diabetes%'
       OR LOWER(DESCRIPTION) LIKE '%hypertension%'
       OR LOWER(DESCRIPTION) LIKE '%hyperlipidemia%'
       OR LOWER(DESCRIPTION) LIKE '%asthma%'
)
SELECT
    (SELECT COUNT(*) FROM patients) AS total_patients,
    (SELECT COUNT(*) FROM chronic_patients) AS chronic_patients,
    (SELECT COUNT(*) FROM patients) - (SELECT COUNT(*) FROM chronic_patients) AS non_chronic_patients;


-- Q1: average distinct medications per patient, chronic vs non-chronic
-- ("all patients" variant -- a patient with zero medication records
-- counts as 0 in the average via COALESCE).
WITH chronic_patients AS (
    SELECT DISTINCT PATIENT
    FROM conditions
    WHERE LOWER(DESCRIPTION) LIKE '%diabetes%'
       OR LOWER(DESCRIPTION) LIKE '%hypertension%'
       OR LOWER(DESCRIPTION) LIKE '%hyperlipidemia%'
       OR LOWER(DESCRIPTION) LIKE '%asthma%'
),
per_patient_meds AS (
    SELECT PATIENT AS patient_id, COUNT(DISTINCT DESCRIPTION) AS distinct_med_count
    FROM medications
    GROUP BY PATIENT
),
patient_flagged AS (
    SELECT
        p.Id AS patient_id,
        COALESCE(pm.distinct_med_count, 0) AS distinct_med_count,
        CASE WHEN cp.PATIENT IS NOT NULL THEN 1 ELSE 0 END AS is_chronic
    FROM patients p
    LEFT JOIN per_patient_meds pm ON pm.patient_id = p.Id
    LEFT JOIN chronic_patients cp ON cp.PATIENT = p.Id
)
SELECT is_chronic, COUNT(*) AS num_patients, ROUND(AVG(distinct_med_count), 2) AS avg_distinct_meds
FROM patient_flagged
GROUP BY is_chronic;


-- Q1b: same comparison, but restricted to patients who have at least one
-- medication record ("prescribed patients only" variant). This is the
-- denominator the PySpark implementation (pyspark/pyspark_analysis.py, q2)
-- uses, since it groups starting from the medications table -- a patient
-- with zero medication rows never appears in that groupBy at all. This
-- variant reproduces the PySpark numbers exactly on the same subset.
WITH chronic_patients AS (
    SELECT DISTINCT PATIENT
    FROM conditions
    WHERE LOWER(DESCRIPTION) LIKE '%diabetes%'
       OR LOWER(DESCRIPTION) LIKE '%hypertension%'
       OR LOWER(DESCRIPTION) LIKE '%hyperlipidemia%'
       OR LOWER(DESCRIPTION) LIKE '%asthma%'
),
per_patient_meds AS (
    SELECT PATIENT AS patient_id, COUNT(DISTINCT DESCRIPTION) AS distinct_med_count
    FROM medications
    GROUP BY PATIENT
),
patient_flagged AS (
    SELECT
        pm.patient_id,
        pm.distinct_med_count,
        CASE WHEN cp.PATIENT IS NOT NULL THEN 1 ELSE 0 END AS is_chronic
    FROM per_patient_meds pm
    LEFT JOIN chronic_patients cp ON cp.PATIENT = pm.patient_id
)
SELECT is_chronic, COUNT(*) AS num_patients, ROUND(AVG(distinct_med_count), 2) AS avg_distinct_meds
FROM patient_flagged
GROUP BY is_chronic;


-- Q2: most-prescribed medication per chronic condition. Joined on
-- (PATIENT, ENCOUNTER), not PATIENT alone -- joining on PATIENT only would
-- pair a condition from one visit with a medication from an unrelated
-- visit for the same patient (the join bug documented in
-- pyspark/pyspark_analysis.py's comments and corrected there).
SELECT
    c.DESCRIPTION AS condition,
    m.DESCRIPTION AS medication,
    COUNT(*) AS times_prescribed
FROM conditions c
JOIN medications m
    ON c.PATIENT = m.PATIENT AND c.ENCOUNTER = m.ENCOUNTER
WHERE LOWER(c.DESCRIPTION) LIKE '%diabetes%'
   OR LOWER(c.DESCRIPTION) LIKE '%hypertension%'
   OR LOWER(c.DESCRIPTION) LIKE '%hyperlipidemia%'
   OR LOWER(c.DESCRIPTION) LIKE '%asthma%'
GROUP BY c.DESCRIPTION, m.DESCRIPTION
ORDER BY times_prescribed DESC
LIMIT 20;


-- Q3: total and average medication cost per chronic condition, again
-- joined on (PATIENT, ENCOUNTER).
SELECT
    c.DESCRIPTION AS condition,
    ROUND(SUM(m.TOTALCOST), 2) AS total_cost,
    ROUND(AVG(m.TOTALCOST), 2) AS avg_cost,
    COUNT(*) AS num_prescriptions
FROM conditions c
JOIN medications m
    ON c.PATIENT = m.PATIENT AND c.ENCOUNTER = m.ENCOUNTER
WHERE LOWER(c.DESCRIPTION) LIKE '%diabetes%'
   OR LOWER(c.DESCRIPTION) LIKE '%hypertension%'
   OR LOWER(c.DESCRIPTION) LIKE '%hyperlipidemia%'
   OR LOWER(c.DESCRIPTION) LIKE '%asthma%'
GROUP BY c.DESCRIPTION
ORDER BY total_cost DESC;
