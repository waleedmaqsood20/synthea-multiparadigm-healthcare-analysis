# mongo_queries.py
#
# these are my mongodb queries for Task 2. using the patients collection
# i built earlier in the synthea_nosql database. same research question
# as assignment 1, how do chronic conditions affect what medicines people
# get prescribed.
#
# Before running this: copy .env.example to .env and set your own
# MONGODB_URI (same database load_synthea_to_mongo.py wrote to).
#
# run with: python mongo_queries.py

import os

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.environ.get("MONGODB_URI")
if not MONGO_URI:
    raise RuntimeError(
        "MONGODB_URI environment variable is not configured. "
        "Copy .env.example to .env and set your own connection string."
    )

client = MongoClient(MONGO_URI)
db = client["synthea_nosql"]
patients = db["patients"]

print("=" * 60)
print("query 1 - just checking basic counts first")
print("=" * 60)
total_patients = patients.count_documents({})
chronic_patients = patients.count_documents({"has_chronic_condition": True})
print("total patients:", total_patients)
print("patients with a chronic condition:", chronic_patients)


print("\n" + "=" * 60)
print("query 2 - pulling a few chronic condition patients")
print("=" * 60)
# this one's simple, just filtering on the has_chronic_condition flag
# i added when i built the documents. no join needed since the flag
# already lives right on the patient
chronic_sample = patients.find(
    {"has_chronic_condition": True},
    {"_id": 1, "gender": 1, "birthdate": 1}
).limit(5)

for p in chronic_sample:
    print(p)


print("\n" + "=" * 60)
print("query 3 - medications per chronic condition")
print("=" * 60)
# this is basically the mongodb version of my main sql query. instead of
# joining two tables, i use $unwind to flatten out the encounters array,
# then flatten the conditions inside each encounter, then the medications,
# then group by condition + medication and count how many times each
# combo shows up. took me a bit to get the unwind order right

pipeline = [
    {"$match": {"has_chronic_condition": True}},
    {"$unwind": "$encounters"},
    {"$unwind": "$encounters.conditions"},
    {"$match": {"encounters.conditions.is_chronic": True}},
    {"$unwind": "$encounters.medications"},
    {
        "$group": {
            "_id": {
                "condition": "$encounters.conditions.description",
                "medication": "$encounters.medications.description",
            },
            "prescription_count": {"$sum": 1},
        }
    },
    {"$sort": {"prescription_count": -1}},
    {"$limit": 20},
]

results = list(patients.aggregate(pipeline))
for r in results:
    print(r["_id"]["condition"], "-", r["_id"]["medication"], ":", r["prescription_count"])


print("\n" + "=" * 60)
print("query 4 - average medications, chronic vs non chronic")
print("=" * 60)
# same comparison as my sql assignment (see results/verified_results.md for
# how the SQL and PySpark denominators lined up). here i unwind encounters
# and medications per patient, count how many distinct medications each
# patient has, then average that by whether they're chronic or not
#
# heads up: preserveNullAndEmptyArrays keeps patients with zero encounters
# or zero medications in the pipeline as a row with a null medication, and
# $addToSet will still add that null to the set -- so a zero-medication
# patient could come out with med_count == 1 instead of 0. i haven't
# re-run this against live data recently to check, so don't fully trust
# these numbers until i do (see results/verified_results.md)

pipeline2 = [
    {"$unwind": {"path": "$encounters", "preserveNullAndEmptyArrays": True}},
    {"$unwind": {"path": "$encounters.medications", "preserveNullAndEmptyArrays": True}},
    {
        "$group": {
            "_id": {"patient": "$_id", "chronic": "$has_chronic_condition"},
            "medications": {"$addToSet": "$encounters.medications.description"},
        }
    },
    {
        "$project": {
            "chronic": "$_id.chronic",
            "med_count": {"$size": "$medications"},
        }
    },
    {
        "$group": {
            "_id": "$chronic",
            "avg_medications": {"$avg": "$med_count"},
            "patient_count": {"$sum": 1},
        }
    },
]

results2 = list(patients.aggregate(pipeline2))
for r in results2:
    label = "chronic condition patient" if r["_id"] else "no chronic condition"
    print(label, "- avg medications:", round(r["avg_medications"], 2), "- patients:", r["patient_count"])


print("\n" + "=" * 60)
print("query 5 - medication cost by chronic condition")
print("=" * 60)
# same idea as the cost query from sql, except i didn't have to fix a
# join bug this time since the medications are already nested right
# inside the same encounter as the condition, there's nothing to
# accidentally join wrong

pipeline3 = [
    {"$match": {"has_chronic_condition": True}},
    {"$unwind": "$encounters"},
    {"$unwind": "$encounters.conditions"},
    {"$match": {"encounters.conditions.is_chronic": True}},
    {"$unwind": "$encounters.medications"},
    {
        "$group": {
            "_id": "$encounters.conditions.description",
            "total_cost": {"$sum": "$encounters.medications.totalcost"},
            "avg_cost": {"$avg": "$encounters.medications.totalcost"},
            "prescriptions": {"$sum": 1},
        }
    },
    {"$sort": {"total_cost": -1}},
]

results3 = list(patients.aggregate(pipeline3))
for r in results3:
    print(r["_id"], "- total cost:", round(r["total_cost"], 2), "- avg cost:", round(r["avg_cost"], 2), "- prescriptions:", r["prescriptions"])


client.close()
print("\ndone")
