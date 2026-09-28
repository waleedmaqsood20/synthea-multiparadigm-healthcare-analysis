# Results

Numbers below came from running `sql/analysis_queries.sql` (SQLite) and
`pyspark/pyspark_analysis.py` (PySpark 3.5, Java 17) against the same
5,000-patient subset (`data/subset/`, seed 42 — see
`scripts/subset_synthea_data.py`).

I didn't re-run the MongoDB pipeline live for this — see the "MongoDB"
section below for why.

## Chronic-condition definition

A condition counts as "chronic" here if its `DESCRIPTION` contains, case
insensitively, `diabetes`, `hypertension`, `hyperlipidemia`, or `asthma` as a
substring. A patient is "chronic" if they have at least one such condition on
record, in any encounter. That substring match also picks up related
descriptions like *Prediabetes*, *Childhood asthma*, and *Diabetic
retinopathy associated with type II diabetes mellitus (disorder)* — that's
intentional, and the same rule is used across the SQL, MongoDB, and PySpark
versions.

## Q1 — average distinct medications, chronic vs non-chronic

I checked two denominators here, because the SQL and PySpark versions
originally handled zero-medication patients differently:

| Variant | Chronic avg | Chronic n | Non-chronic avg | Non-chronic n |
|---|---:|---:|---:|---:|
| SQL — all patients (0 for no medications) | 6.20 | 2,717 | 3.75 | 2,283 |
| SQL — patients with ≥1 medication only | **6.3** | 2,675 | **4.11** | 2,088 |
| PySpark (`pyspark_analysis.py`, q2) | **6.3** | 2,675 | **4.11** | 2,088 |

The "patients with ≥1 medication" SQL variant matches the PySpark result
exactly — same counts, same averages. That's a good sign: the 6.3 / 4.11
split (roughly a 53% relative difference) isn't a one-off or a stale number,
it holds up once both queries are counting the same denominator.

The "all patients" variant comes out lower on both sides because it counts
the 42 chronic and 195 non-chronic patients with zero medication records as
0 instead of leaving them out. Neither one is "wrong" — it's a scope
decision — so I kept both queries in `sql/analysis_queries.sql` (Q1 and Q1b)
instead of picking one silently.

## Q2 — most-prescribed medication per chronic condition

Matches exactly between `sql/analysis_queries.sql` (Q2) and
`pyspark/pyspark_analysis.py` (q1), joined on `(PATIENT, ENCOUNTER)`. Top 3:

| Condition | Medication | Times prescribed |
|---|---|---:|
| Hypertension | lisinopril 10 MG Oral Tablet | 955 |
| Hypertension | Hydrochlorothiazide 25 MG Oral Tablet | 555 |
| Hypertension | amLODIPine 2.5 MG Oral Tablet | 455 |

## Q3 — total/average medication cost per chronic condition

Also matches exactly between `sql/analysis_queries.sql` (Q3) and
`pyspark/pyspark_analysis.py` (q3), joined on `(PATIENT, ENCOUNTER)`. Top 3:

| Condition | Total cost | Avg cost | Prescriptions |
|---|---:|---:|---:|
| Hypertension | $16,627,326.16 | $6,865.12 | 2,422 |
| Prediabetes | $15,187,443.57 | $11,367.85 | 1,336 |
| Diabetes | $13,931,977.32 | $19,430.93 | 717 |

## MongoDB

`mongodb/mongo_queries.py` (query 4) implements the same Q1 comparison as an
aggregation pipeline over the embedded patient documents. I didn't run it
live against the database for this comparison — mostly because of the
credential situation described below, and I didn't want to touch that
database again before rotating it.

Reading through the pipeline, there's one thing worth double-checking once I
do run it again: both `$unwind` stages use `preserveNullAndEmptyArrays: true`,
so a patient with zero encounters or zero medications still produces a row
with a `null` medication description, and `$addToSet` will add that `null`
into the set — meaning a zero-medication patient could come out with
`med_count == 1` instead of `0`. That would be a third denominator
convention, different from both SQL variants above. I haven't confirmed this
against a live run yet, so treat the MongoDB numbers as unverified for now.

## Sample sizes

- Full CSIRO collection (per official metadata): 117,258 synthetic Queensland patients.
- My working subset: 5,000 patients (random sample, seed 42).
- 8 of the 17 official CSV tables used: `patients`, `encounters`, `conditions`,
  `medications`, `procedures`, `immunizations`, `organizations`, `providers`.

## Security note

A MongoDB Atlas connection string with a plaintext username/password had
been hardcoded in `load_synthea_to_mongo.py` and `mongo_queries.py`. I've
removed it from both files here and replaced it with an environment-variable
requirement (`MONGODB_URI`, loaded via `.env` / `python-dotenv`). That old
credential still needs to be rotated in Atlas — pulling it out of the source
code doesn't undo the fact it was exposed.
