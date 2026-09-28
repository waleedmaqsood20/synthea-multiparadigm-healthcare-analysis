# Data

This repository does not include raw data. The dataset is synthetic
healthcare data, distributed separately, and is large enough (multi-gigabyte
CSVs for the full population) that it does not belong in a git repository.

## Source dataset

**Australian synthetic healthcare data with Synthea**
Author: Ibrahima Diouf
Publisher: CSIRO, Data Access Portal
DOI: [10.25919/efcw-bm49](https://doi.org/10.25919/efcw-bm49)
Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)

The dataset was generated with an Australianised version of
[Synthea](https://synthetichealth.github.io/synthea/), a synthetic patient
and clinical data generator. It contains **117,258 fully synthetic patients**
from Queensland, generated from population-level demographic and disease
statistics. **It does not contain, and was never derived from, real patient
records.**

## Tables used by this project

The full CSIRO collection ships three data formats (per-patient FHIR JSON,
a 300k-patient bulk FHIR export, and CSV tables). This project only uses
8 of the 17 available CSV tables:

| File | Used for |
|---|---|
| `patients.csv` | patient demographics |
| `encounters.csv` | visit/encounter records |
| `conditions.csv` | diagnosed conditions per encounter |
| `medications.csv` | prescriptions per encounter |
| `procedures.csv` | procedures per encounter |
| `immunizations.csv` | immunization records |
| `organizations.csv` | reference table: healthcare organisations |
| `providers.csv` | reference table: individual providers |

`allergies.csv`, `careplans.csv`, `claims.csv`, `devices.csv`,
`imaging_studies.csv`, `payers.csv`, `payer_transitions.csv`, `sample.csv`,
and `supplies.csv` are part of the official collection but are **not used**
here.

## Obtaining the data

1. Download the collection from the CSIRO Data Access Portal via the DOI
   above (registration/access terms are set by CSIRO, not this repository).
2. Place the 8 CSV files listed above into `data/raw/` in this repository
   (this folder is git-ignored).
3. Verify file integrity against the checksum manifest CSIRO provides with
   the download (`collection_import_sha256sum.txt`), e.g.:
   ```
   sha256sum -c collection_import_sha256sum.txt --ignore-missing
   ```

## Building the working subset

The full CSV export is large (~117k patients, several GB across the 8
tables). All analysis in this project runs against a reproducible
5,000-patient random sample instead:

```
python scripts/subset_synthea_data.py --input-dir data/raw --output-dir data/subset
```

This samples 5,000 patients with a fixed random seed (42), then filters
`encounters`, `conditions`, `medications`, `procedures`, and `immunizations`
down to that cohort. `organizations.csv` and `providers.csv` are copied
as-is since they are small reference tables shared across all patients.
`data/subset/` is also git-ignored — regenerate it rather than committing it.

## SQLite database

`sql/schema.sql` defines the schema for the 8 tables above. Build a local
SQLite database from `data/subset/*.csv` (see `sql/schema.sql` for the
loading command) rather than committing a `.db` file — it is fully
reproducible from the CSVs and regeneration is fast at this subset size.
