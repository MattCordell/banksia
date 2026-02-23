# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Always ask clarifying questions if the answer is not obvious. You can provide recommendations, but if there is anything you are unclear of - you should ask for further information to help come to a decision.

You do not need to wask permission to perform Web Searches. Research is encouraged, especially using reputable sources to come to accurate decisions and answers. You have permission to search the web for any publicly available information.

## Project Overview

Modular synthetic patient data generator for a data-golf exercise. Python project (>=3.10).

## Architecture

```
common/          Shared utilities (sampling, config loading, PatientContext dataclass)
conditions/      Condition assignment (epidemiology-weighted, SNOMED CT coding via Ontoserver)
laboratory/      Lab result generator (consumes PatientContext, returns flat dicts)
medicines/       Medicine assignment (condition-driven, AMT substance ECL via Ontoserver)
population/      Population generator (produces List[PatientContext] from ABS data)
formatters/      Output formatting (CSV; FHIR planned)
tools/           Reference files and analysis scripts (not part of pipeline)
generate.py      CLI orchestrator (single patient, cohort, population-only modes)
```

### Key patterns
- **PatientContext** (`common/types.py`) bridges modules: population produces them, lab consumes them
- Generators return plain data (dicts/lists), formatters handle serialisation
- Config-driven: lab panels in JSON (`laboratory/panels.json`, `laboratory/conditions.json`), condition epidemiology in `conditions/epidemiology.json`, medicine prescriptions in `medicines/prescriptions.json`
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

# Medicine ECL templates (select product level instead of raw ingredients)
# Named templates defined in medicines/ecl_templates.json
python generate.py --mode single --condition "Hypothyroidism" --sex female --age 54 \
  --med-ecl-template amt-tpuu
```

## References

When making changes that are informed by external sources (clinical data, reference intervals, population statistics, formulas, panel specifications), update `References.md` with the source details. Only document sources that substantially informed data choices — not incidental information.
