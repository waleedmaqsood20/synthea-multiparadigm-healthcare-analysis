# load_synthea_to_mongo.py
#
# This script takes the smaller CSV files I already made for Assignment 1
# (the data/subset folder) and loads them into MongoDB.
#
# Basic idea: instead of having separate tables like in SQL, I'm building
# one big document per patient. Each patient document has their encounters
# inside it, and each encounter has the conditions and medications from
# that same visit inside it. This is the "embedding" part of my NoSQL
# design from Task 1.
#
# Providers and organizations are NOT embedded, I just store their ID
# and reference them, because the same provider/org shows up across
# thousands of patients so embedding them everywhere would be wasteful.
#
# Before running this:
# - pip install -r requirements.txt
# - make sure data/subset exists (run scripts/subset_synthea_data.py first)
# - copy .env.example to .env and set your own MONGODB_URI

import os

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBSET_DIR = os.environ.get("SYNTHEA_SUBSET_DIR", os.path.join(REPO_ROOT, "data", "subset"))

MONGO_URI = os.environ.get("MONGODB_URI")
if not MONGO_URI:
    raise RuntimeError(
        "MONGODB_URI environment variable is not configured. "
        "Copy .env.example to .env and set your own connection string."
    )

DB_NAME = "synthea_nosql"
COLLECTION_NAME = "patients"

# same chronic condition list I used in my SQL assignment, keeping it
# consistent since I'm answering the same research question here
CHRONIC_KEYWORDS = ["diabetes", "hypertension", "hyperlipidemia", "asthma"]


def is_chronic(description):
    # just checking if any of my chronic keywords show up in the condition name
    desc_lower = str(description).lower()
    for keyword in CHRONIC_KEYWORDS:
        if keyword in desc_lower:
            return True
    return False


def path(name):
    return os.path.join(SUBSET_DIR, name)


print("loading csv files...")
patients_df = pd.read_csv(path("patients.csv"))
encounters_df = pd.read_csv(path("encounters.csv"))
conditions_df = pd.read_csv(path("conditions.csv"))
medications_df = pd.read_csv(path("medications.csv"))

print("patients:", len(patients_df))
print("encounters:", len(encounters_df))
print("conditions:", len(conditions_df))
print("medications:", len(medications_df))

# first I'm grouping conditions and medications by their encounter id
# so I can quickly grab "everything that happened in this visit" later
print("grouping conditions and medications by encounter...")

conditions_by_encounter = {}
for i, row in conditions_df.iterrows():
    enc_id = row["ENCOUNTER"]
    if enc_id not in conditions_by_encounter:
        conditions_by_encounter[enc_id] = []
    conditions_by_encounter[enc_id].append({
        "code": str(row.get("CODE", "")),
        "description": row.get("DESCRIPTION", ""),
        "start": row.get("START", ""),
        "is_chronic": is_chronic(row.get("DESCRIPTION", "")),
    })

medications_by_encounter = {}
for i, row in medications_df.iterrows():
    enc_id = row["ENCOUNTER"]
    if enc_id not in medications_by_encounter:
        medications_by_encounter[enc_id] = []
    medications_by_encounter[enc_id].append({
        "code": str(row.get("CODE", "")),
        "description": row.get("DESCRIPTION", ""),
        "totalcost": float(row.get("TOTALCOST", 0) or 0),
        "start": row.get("START", ""),
    })

# now group encounters by patient, and pull in the conditions/medications
# for each encounter using the dictionaries I just built above
print("grouping encounters by patient...")

encounters_by_patient = {}
for i, row in encounters_df.iterrows():
    pat_id = row["PATIENT"]
    enc_id = row["Id"]
    if pat_id not in encounters_by_patient:
        encounters_by_patient[pat_id] = []
    encounters_by_patient[pat_id].append({
        "encounter_id": enc_id,
        "start": row.get("START", ""),
        "stop": row.get("STOP", ""),
        "encounterclass": row.get("ENCOUNTERCLASS", ""),
        "description": row.get("DESCRIPTION", ""),
        "provider_id": row.get("PROVIDER", ""),
        "organization_id": row.get("ORGANIZATION", ""),
        "conditions": conditions_by_encounter.get(enc_id, []),
        "medications": medications_by_encounter.get(enc_id, []),
    })

# now build the actual patient documents that will go into mongodb
print("building patient documents...")

patient_documents = []
for i, row in patients_df.iterrows():
    pat_id = row["Id"]
    patient_encounters = encounters_by_patient.get(pat_id, [])

    # quick flag so I can filter chronic vs non chronic patients easily
    # later on without having to dig through every encounter each time
    has_chronic = False
    for enc in patient_encounters:
        for cond in enc["conditions"]:
            if cond["is_chronic"]:
                has_chronic = True

    doc = {
        "_id": pat_id,
        "birthdate": row.get("BIRTHDATE", ""),
        "gender": row.get("GENDER", ""),
        "race": row.get("RACE", ""),
        "ethnicity": row.get("ETHNICITY", ""),
        "marital": row.get("MARITAL", "") if pd.notna(row.get("MARITAL")) else None,
        "city": row.get("CITY", ""),
        "state": row.get("STATE", ""),
        "has_chronic_condition": has_chronic,
        "encounters": patient_encounters,
    }
    patient_documents.append(doc)

print("total patient documents built:", len(patient_documents))

# connect and push everything in
print("connecting to mongodb...")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# clearing out old data first in case I run this more than once
print("clearing old data if any exists...")
collection.delete_many({})

# inserting in batches instead of all at once so it doesn't choke
print("inserting patient documents, this might take a bit...")
batch_size = 500
for i in range(0, len(patient_documents), batch_size):
    batch = patient_documents[i:i + batch_size]
    collection.insert_many(batch)
    print("inserted", min(i + batch_size, len(patient_documents)), "of", len(patient_documents))

print("")
print("done!")
print("total patients in mongodb:", collection.count_documents({}))
print("patients with a chronic condition:", collection.count_documents({"has_chronic_condition": True}))

client.close()
