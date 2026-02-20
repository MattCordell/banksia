# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Modular synthetic patient data generator for a data-golf exercise. Python project (>=3.10).

## Architecture

```
common/          Shared utilities (sampling, config loading, PatientContext dataclass)
conditions/      Condition assignment (epidemiology-weighted, SNOMED CT coding via Ontoserver)
laboratory/      Lab result generator (consumes PatientContext, returns flat dicts)
population/      Population generator (produces List[PatientContext] from ABS data)
formatters/      Output formatting (CSV; FHIR planned)
tools/           Reference files and analysis scripts (not part of pipeline)
generate.py      CLI orchestrator (single patient, cohort, population-only modes)
```

### Key patterns
- **PatientContext** (`common/types.py`) bridges modules: population produces them, lab consumes them
- Generators return plain data (dicts/lists), formatters handle serialisation
- Config-driven: lab panels in JSON (`laboratory/panels.json`, `laboratory/conditions.json`), condition epidemiology in `conditions/epidemiology.json`
- Condition assignment uses Australian prevalence data (AIHW/ABS) with age, sex, and lifestyle multipliers
- SNOMED CT coding via Ontoserver FHIR ValueSet/$expand (cached per ECL+edition)
- New generator modules should follow the same interface: accept PatientContext, return dicts

### Running
```bash
python generate.py --mode single --condition "Hypothyroidism" --sex female --age 54
python generate.py --mode cohort --n 200 --output cohort.csv
python generate.py --mode population --n 200 --output population.csv

# SNOMED CT options
python generate.py --mode single --sex female --age 54 --snomed-edition 20250131
python generate.py --mode cohort --n 100 --no-snomed --output offline.csv
python generate.py --mode single --tx-server https://tx.ontoserver.csiro.au/fhir
```

## References

When making changes that are informed by external sources (clinical data, reference intervals, population statistics, formulas, panel specifications), update `References.md` with the source details. Only document sources that substantially informed data choices — not incidental information.
