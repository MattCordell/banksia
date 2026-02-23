# Adding New Conditions

This guide explains how to add a new medical condition to the synthetic patient data generator.

## Overview

Each condition requires entries in four files:

| File | Purpose |
|------|---------|
| `conditions/epidemiology.json` | Prevalence, age/sex distribution, lifestyle risk factors, SNOMED ECL |
| `laboratory/conditions.json` | Lab result overrides (shifted means/SDs for affected tests) |
| `medicines/prescriptions.json` | Medicine categories with probabilities and AMT substance ECL |
| `References.md` | Clinical sources that informed your data choices |

Optionally, you may also need to update:

| File | When |
|------|------|
| `conditions/snomed_exclusions.json` | If the SNOMED ECL returns codes that are sex- or age-inappropriate |

No Python code changes are needed — the system is entirely config-driven.

## Step 1: Epidemiology Entry

Add an entry to `conditions/epidemiology.json`. The condition name must match exactly between this file and `laboratory/conditions.json`.

```json
"Condition Name": {
  "ecl": "<<SNOMED_CONCEPT_ID",
  "base_prevalence": 0.03,
  "sex_ratio": { "male": 1.0, "female": 1.0, "other": 1.0 },
  "age_prevalence": [
    { "min_age": 0, "max_age": 17, "multiplier": 0.1 },
    { "min_age": 18, "max_age": 64, "multiplier": 1.0 },
    { "min_age": 65, "max_age": 200, "multiplier": 2.0 }
  ],
  "lifestyle_multipliers": {
    "smoker": 1.5
  },
  "notes": "Source and rationale for prevalence figures."
}
```

### Field reference

- **ecl**: SNOMED CT Expression Constraint Language query. Use `<<` for descendants-or-self. You can test ECL expressions against the CSIRO Ontoserver at `https://r4.ontoserver.csiro.au/fhir`.
- **base_prevalence**: Point prevalence as a decimal (e.g., 0.03 = 3%). This is the overall population probability before age/sex/lifestyle adjustments. For acute conditions (infections, injuries), use point prevalence, not lifetime prevalence.
- **sex_ratio**: Multipliers relative to 1.0. Values >1 increase likelihood for that sex. The ratios do not need to sum to any particular value.
- **age_prevalence**: Array of age bands with multipliers. Must cover 0-200 with no gaps. The multiplier scales the base prevalence for that age range (1.0 = baseline rate).
- **lifestyle_multipliers**: Optional multipliers for lifestyle factors. Available factors: `smoker`, `heavy_drinker`, `high_bmi`, `sedentary`, `athlete`.
- **notes**: Brief description of data sources. Include specific statistics that informed your choices.

### Prevalence guidelines

Use Australian data where possible (AIHW, ABS, NNDSS). For the existing conditions, base prevalence ranges from 0.002 (parasitic infection) to 0.116 (hypertension). Consider:

- Is this a chronic condition (higher point prevalence) or acute (lower)?
- What age groups are most affected?
- Are there strong sex differences?

## Step 2: Lab Result Overrides

Add an entry to `laboratory/conditions.json`. This defines how lab results shift for patients with this condition.

```json
"Condition Name": {
  "inherits": "Healthy",
  "panel_overrides": {
    "FBC": {
      "WBC (×10^9/L)": {
        "mean": 14.0,
        "sd": 5.0,
        "min": 4.0,
        "max": 40.0,
        "distribution": "lognormal"
      },
      "differential_props": {
        "neutrophils": 0.75,
        "lymphocytes": 0.15,
        "monocytes": 0.06,
        "eosinophils": 0.02,
        "basophils": 0.02
      }
    },
    "CRP": {
      "CRP (mg/L)": {
        "mean": 120,
        "sd": 80,
        "min": 10,
        "max": 500,
        "distribution": "lognormal"
      }
    }
  },
  "notes": "Brief clinical rationale for the overrides."
}
```

### Field reference

- **inherits**: Always set to `"Healthy"`. The system merges your overrides on top of the healthy baseline.
- **panel_overrides**: Only include panels and tests that are affected by this condition. Tests not listed will use the healthy baseline from `laboratory/panels.json`.
- **distribution**: Either `"normal"` or `"lognormal"`. Use lognormal for values that are always positive and can have a long right tail (e.g., WBC, CRP, liver enzymes, ferritin). Use normal for values that cluster symmetrically (e.g., sodium, albumin, haemoglobin).
- **differential_props**: FBC-specific. The five values are base proportions for Dirichlet sampling and must sum to 1.0. They control the WBC differential (neutrophils, lymphocytes, monocytes, eosinophils, basophils).

### Available panels and tests

Only override tests that already exist in `laboratory/panels.json`. The available panels are:

| Panel | Key tests |
|-------|-----------|
| MBAP | Sodium, Potassium, Chloride, Bicarbonate, Calcium, Phosphate, Urea, Urate, Creatinine, eGFR (calculated), Glucose, Total Protein, Albumin, Globulin, Bilirubin, ALP, AST, ALT, GGT, LDH, Cholesterol |
| FBC | WBC, Haemoglobin, Platelets, MCV, differential_props |
| LFT | ALT, AST, GGT, ALP, Bilirubin, Albumin |
| Lipid Panel | Total Cholesterol, HDL, LDL, Triglycerides |
| Iron Studies | Ferritin, Serum Iron, Transferrin, Transferrin Saturation |
| Thyroid Panel | TSH, Free T4 |
| Bone Profile | Calcium, Phosphate, ALP |
| B12 & Folate | Vitamin B12, Folate |
| Kidney Function | Sodium, Potassium, Urea, Creatinine, eGFR (calculated) |
| Immunoglobulins | IgG, IgA, IgM |
| CRP | CRP |

Tests that appear in multiple panels (e.g., Albumin in MBAP and LFT) share values — the first sampled value is reused. Calculated fields (eGFR, Anion Gap) are derived automatically and should not be overridden.

### Tips for choosing values

- **mean**: The typical value for a patient with this condition. Compare against the healthy baseline in `panels.json`.
- **sd**: Controls spread. Larger SD = more variability between patients.
- **min/max**: Hard clamps. These prevent physiologically impossible values.
- Only override tests that are clinically relevant to your condition. A condition that primarily affects the liver doesn't need to override thyroid tests.
- Look at existing conditions in `conditions.json` for examples of how other conditions set their overrides.

## Step 3: Medicine Prescriptions

Add an entry to `medicines/prescriptions.json`. This defines which medicine categories may be prescribed for patients with this condition.

```json
"Condition Name": {
  "medicines": [
    {
      "category": "Drug Class Name",
      "ecl": "372567009 OR 703674001",
      "probability": 0.85,
      "notes": "Brief rationale for this class and probability."
    }
  ],
  "notes": "Overall prescribing rationale."
}
```

### Field reference

- **category**: A human-readable label for the drug class (e.g., "ACE Inhibitors", "Statins"). This appears in the output CSV.
- **ecl**: SNOMED CT ECL expression targeting AMT substance concepts. Use concept IDs from the AMT ingredient reference set. Multiple alternatives are separated with `OR` (e.g., `"386872004 OR 372916001"` for ramipril or perindopril).
- **probability**: Chance (0.0–1.0) that a patient with this condition is prescribed something from this class. Use Australian prescribing data (PBS, Therapeutic Guidelines) to inform this.
- **notes**: Brief clinical rationale.

### Tips for choosing categories

- Only include medicines that are clinically relevant to your condition.
- Probabilities should reflect real-world prescribing patterns, not theoretical maximums. First-line monotherapy might be 0.80–0.95; a specialist-only adjunct might be 0.05–0.15.
- Concept IDs must match entries in the AMT ingredient reference files (`-20260223-1069.csv` for individual ingredients, `-20260223-10327.csv` for combination products).
- Output is capped at 3 medicines per patient, so order categories from most to least commonly prescribed — earlier categories are more likely to appear before the cap is reached.
- Look at existing conditions in `prescriptions.json` for examples of how other conditions set their categories and probabilities.

### ECL templates for product selection

The ECL in `prescriptions.json` should always target **ingredient/substance** concepts. To select specific product types (e.g., AMT trade products), use `--med-ecl-template` at runtime with a named template key:

```bash
# Default: returns ingredient concepts (e.g., "Metformin")
python generate.py --mode single --condition "Type 2 Diabetes Mellitus" --sex male --age 55

# AMT TPUU: returns trade product concepts (e.g., "Glucophage 500 mg tablet")
python generate.py --mode single --condition "Type 2 Diabetes Mellitus" --sex male --age 55 \
  --med-ecl-template amt-tpuu
```

Named templates are defined in `medicines/ecl_templates.json`. Available templates:

| Key | Description |
|-----|-------------|
| `amt-tpuu` | AMT Trade Product Unit of Use |
| `amt-mpuu` | AMT Medicinal Product Unit of Use |
| `amt-tp` | AMT Trade Product |
| `amt-mp` | AMT Medicinal Product |
| `product` | SNOMED CT international medicinal product hierarchy |

You can also pass a raw ECL template string with `{ingredients}` as the placeholder. To add new named templates, add entries to `medicines/ecl_templates.json`.

The ingredient ECL from `prescriptions.json` is substituted into the template's `{ingredients}` placeholder. This keeps the config portable across different drug terminology extensions.

## Step 4: SNOMED Exclusions (if needed)

Check whether the SNOMED ECL for your condition returns codes that would be inappropriate for certain demographics. For example, pregnancy-related codes should not be assigned to males.

If exclusions are needed, add a rule to `conditions/snomed_exclusions.json`:

```json
"rule_name": {
  "ecl": "(ECL expression matching codes to exclude)",
  "exclude_when": { "sex": ["male"], "max_age": 14, "min_age": 55 }
}
```

The exclusion rules are applied globally across all conditions, so check whether an existing rule already covers your case before adding a new one.

## Step 5: Update References

Add entries to `References.md` under the appropriate section. Include:

- Source name and authors (if applicable)
- Key data points that informed your parameter choices
- URL

Group epidemiology and lab pattern sources under separate headings if both are substantial.

## Step 6: Verify

Test your new condition with single-patient generation:

```bash
python generate.py --mode single --condition "Condition Name" --sex male --age 50 --no-snomed
```

Check that:
- The command runs without errors
- Lab values look clinically plausible for the condition
- Key distinguishing features are visible (e.g., elevated CRP, shifted WBC differential)
- Medicine categories are clinically appropriate for the condition

Then test in a cohort to verify prevalence weighting:

```bash
python generate.py --mode cohort --n 200 --no-snomed --output test.csv
```

Check that your condition appears at roughly the expected rate. Remove the test file when done.

To test with SNOMED coding (requires network access to Ontoserver):

```bash
python generate.py --mode single --condition "Condition Name" --sex female --age 45
```

## Checklist

- [ ] Entry added to `conditions/epidemiology.json` with ECL, prevalence, age/sex/lifestyle data
- [ ] Entry added to `laboratory/conditions.json` with panel overrides
- [ ] Condition name matches exactly between all JSON files
- [ ] Entry added to `medicines/prescriptions.json` with medicine categories
- [ ] SNOMED exclusions reviewed (add to `snomed_exclusions.json` if needed)
- [ ] Clinical sources added to `References.md`
- [ ] Single-patient generation tested and produces plausible results
- [ ] Cohort generation tested and condition appears at expected rate
