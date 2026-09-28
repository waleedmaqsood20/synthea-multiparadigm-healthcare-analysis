# pyspark_analysis.py
#
# Task 3, using pyspark now instead of sql or mongodb. same question
# as before, does having a chronic condition change what medicine you
# get. this time doing it with spark dataframes to see how it handles
# things at a bigger scale.
#
# Requires a working Java 17+ install with JAVA_HOME set in your shell
# (PySpark needs a JVM). See README.md "Reproducibility" for setup notes
# on Windows/macOS/Linux.
#
# run with: python pyspark_analysis.py

import os
import sys

if not os.environ.get("JAVA_HOME"):
    sys.exit(
        "JAVA_HOME is not set. Install a JDK (17+) and set JAVA_HOME before "
        "running this script -- see README.md 'Reproducibility' for details."
    )

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("SYNTHEA_SUBSET_DIR", os.path.join(REPO_ROOT, "data", "subset"))

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, avg, sum as spark_sum, when, lower, round as spark_round, datediff, current_date, floor

spark = SparkSession.builder \
    .appName("SyntheaChronic") \
    .master("local[*]") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")  # spark prints a lot of junk otherwise

print("reading the csvs in...")


def data_path(name):
    return os.path.join(DATA_DIR, name)


patients = spark.read.csv(data_path("patients.csv"), header=True, inferSchema=True)
encounters = spark.read.csv(data_path("encounters.csv"), header=True, inferSchema=True)
conditions = spark.read.csv(data_path("conditions.csv"), header=True, inferSchema=True)
medications = spark.read.csv(data_path("medications.csv"), header=True, inferSchema=True)

print("patients:", patients.count())
print("encounters:", encounters.count())
print("conditions:", conditions.count())
print("medications:", medications.count())


print("\n" + "=" * 60)
print("filtering down to the 4 chronic conditions i've been using")
print("=" * 60)

chronic = conditions.filter(
    lower(col("DESCRIPTION")).contains("diabetes") |
    lower(col("DESCRIPTION")).contains("hypertension") |
    lower(col("DESCRIPTION")).contains("hyperlipidemia") |
    lower(col("DESCRIPTION")).contains("asthma")
)

print("rows matching:", chronic.count())


print("\n" + "=" * 60)
print("q1 - medications per condition")
print("=" * 60)
# joining on patient and encounter, same as i had to fix in my sql
# version, otherwise it grabs medicine from a totally different visit

meds_by_condition = chronic.join(
    medications,
    (chronic.PATIENT == medications.PATIENT) & (chronic.ENCOUNTER == medications.ENCOUNTER)
).groupBy(
    chronic.DESCRIPTION.alias("condition"),
    medications.DESCRIPTION.alias("medication")
).agg(
    count("*").alias("times_prescribed")
).orderBy(col("times_prescribed").desc())

meds_by_condition.show(20, truncate=False)


print("\n" + "=" * 60)
print("q2 - avg medicines per patient, chronic vs not")
print("=" * 60)

chronic_ids = chronic.select("PATIENT").distinct()

# using countDistinct here, not count, since i want how many different
# medications a patient has, not how many times they got any prescription
# refilled. mixed this up on my first attempt and got avg of 114 which
# was clearly wrong, so switched to counting distinct medication names.
#
# note: this groups from the medications table, so patients with zero
# medication records never show up here at all -- they're not counted as
# 0, they're just excluded from the denominator. see
# results/verified_results.md for how this compares to the SQL version,
# which also has an "all patients" variant that does count them as 0.
from pyspark.sql.functions import countDistinct

meds_per_patient = medications.groupBy("PATIENT").agg(
    countDistinct("DESCRIPTION").alias("med_count")
)

meds_per_patient_flagged = meds_per_patient.join(
    chronic_ids,
    meds_per_patient.PATIENT == chronic_ids.PATIENT,
    "left"
).select(
    meds_per_patient.PATIENT,
    meds_per_patient.med_count,
    when(chronic_ids.PATIENT.isNotNull(), True).otherwise(False).alias("is_chronic")
)

avg_comparison = meds_per_patient_flagged.groupBy("is_chronic").agg(
    spark_round(avg("med_count"), 2).alias("avg_meds"),
    count("*").alias("num_patients")
)

avg_comparison.show()


print("\n" + "=" * 60)
print("q3 - cost per condition")
print("=" * 60)

cost_by_condition = chronic.join(
    medications,
    (chronic.PATIENT == medications.PATIENT) & (chronic.ENCOUNTER == medications.ENCOUNTER)
).groupBy(
    chronic.DESCRIPTION.alias("condition")
).agg(
    spark_round(spark_sum("TOTALCOST"), 2).alias("total_cost"),
    spark_round(avg("TOTALCOST"), 2).alias("avg_cost"),
    count("*").alias("num_prescriptions")
).orderBy(col("total_cost").desc())

cost_by_condition.show(truncate=False)


print("\n" + "=" * 60)
print("q4 - chronic patients by age group and gender")
print("=" * 60)

chronic_demo = patients.join(
    chronic_ids,
    patients.Id == chronic_ids.PATIENT
).withColumn(
    "age", floor(datediff(current_date(), col("BIRTHDATE")) / 365.25)
).withColumn(
    "age_group",
    when(col("age") < 18, "0-17")
    .when(col("age") < 35, "18-34")
    .when(col("age") < 50, "35-49")
    .when(col("age") < 65, "50-64")
    .otherwise("65+")
)

demo_summary = chronic_demo.groupBy("age_group", "GENDER").agg(
    count("*").alias("num_patients")
).orderBy("age_group", "GENDER")

demo_summary.show(20)


print("\nall done, closing spark")
spark.stop()
