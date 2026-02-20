# References

Sources that substantially informed data choices and parameters in this project.

## Population Statistics

- **Australian Bureau of Statistics (ABS) — Population by Age and Sex (Cat. 3235.0)**
  Data file: `32350DS0001_2024.xlsx`
  Used to weight synthetic population generation by state, age group, and sex.
  https://www.abs.gov.au/statistics/people/population/population-projections-australia

- **ABS National Health Survey (2022-23) — Smoking, Alcohol, Physical Activity, BMI**
  Informed age- and sex-specific rates for lifestyle factor assignment (smoker, heavy_drinker, sedentary, athlete, high_bmi).
  https://www.abs.gov.au/statistics/health/health-conditions-and-risks

- **ABS — Adult Height and Weight Statistics**
  Australian adult mean height/weight by sex used for `generate_height_weight()`.
  https://www.abs.gov.au/statistics/health/health-conditions-and-risks/national-health-survey

## Clinical Reference Intervals

- **AACB/RCPA Harmonised Reference Intervals for Chemical Pathology**
  Primary source for baseline mean and SD derivation across all panels. Reference intervals treated as mean +/- 2 SD for normally distributed analytes.
  https://www.rcpa.edu.au/Manuals/RCPA-Manual/General-Information/IG/Table-6-Harmonised-reference-intervals-for-chem

- **Harmonising Adult and Paediatric Reference Intervals in Australia and New Zealand (AACB, 2015)**
  Jones GRD, et al. *Clinical Biochemist Reviews*. 2015;36(1):21-26.
  Provided the first harmonised panel of 11 chemistry analytes (sodium, potassium, chloride, bicarbonate, creatinine, calcium, phosphate, magnesium, LDH, ALP, total protein).
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4310061/

## Laboratory Panels

- **Sullivan Nicolaides Pathology — E/LFT, EUC and LFT Panels (March 2023)**
  Definitive reference for the MBAP (Multiple Biochemistry Analysis Panel / E-LFT) test composition: 22 tests spanning electrolytes, liver function, glucose, urate, calcium, phosphate, LDH, and cholesterol.
  File: `Laboratory/e-lft-euc-and-lft-profiles-202303.pdf`
  https://www.snp.com.au/media/0dwkxb5p/e-lft-euc-and-lft-profiles-202303.pdf

- **Austin Pathology — Multiple Biochemical Analysis 20 (MBA 20) Test Directory**
  Confirmed MBA 20 component groupings (UEC, LFT, glucose, urate, lipids, calcium, magnesium, phosphate).
  https://www.austinpathology.org.au/test-directory/1759

## Calculated Values

- **2021 CKD-EPI Creatinine Equation (Race-Free)**
  Inker LA, et al. *New England Journal of Medicine*. 2021;385(19):1737-1749.
  Used for eGFR calculation from creatinine, age, and sex.
  https://www.nejm.org/doi/full/10.1056/NEJMoa2102953

## Condition Epidemiology

Prevalence rates used in `conditions/epidemiology.json` for demographic-weighted condition assignment.

- **AIHW — Diabetes: Type 2 Diabetes**
  4.6% diagnosed Australian adults (NDSS 2021). Age/sex stratification. M 1.3x higher.
  https://www.aihw.gov.au/reports/diabetes/diabetes/contents/how-common-is-diabetes/type-2-diabetes

- **ABS — Hypertension and High Measured Blood Pressure (2022)**
  11.6% self-reported. Age stratification: 2% at 18-34, 45% at 75+.
  https://www.abs.gov.au/statistics/health/health-conditions-and-risks/hypertension-and-high-measured-blood-pressure/latest-release

- **ABS — High Cholesterol (2022)**
  8.4% self-reported hyperlipidaemia.
  https://www.abs.gov.au/statistics/health/health-conditions-and-risks/high-cholesterol/latest-release

- **AIHW — Heart, Stroke and Vascular Disease: Australian Facts**
  IHD ~3% adults, Heart Failure ~0.7%. Sex and age stratification.
  https://www.aihw.gov.au/reports/heart-stroke-vascular-diseases/hsvd-facts/contents/summary

- **AIHW — Chronic Kidney Disease**
  Stages 3-4 ~4% of adults. Strong age gradient (44% at 75+).
  https://www.aihw.gov.au/reports/chronic-kidney-disease/chronic-kidney-disease/contents/how-many-people-are-living-with-ckd

- **AIHW — COPD**
  2.5% overall; 4.8% in 45+. Smoking dominant risk factor.
  https://www.aihw.gov.au/reports/chronic-respiratory-conditions/copd

- **AIHW — Osteoarthritis**
  8.3% overall. F 10% vs M 6.1%.
  https://www.aihw.gov.au/reports/chronic-musculoskeletal-conditions/osteoarthritis

- **AIHW — Rheumatoid Arthritis**
  2.0% overall. F 2.5% vs M 1.6%.
  https://www.aihw.gov.au/reports/chronic-musculoskeletal-conditions/rheumatoid-arthritis

- **AIHW — Liver Disease Quick Facts**
  Alcoholic liver disease, cirrhosis prevalence and sex ratios.
  https://www.aihw.gov.au/getmedia/a088f80f-fcdb-4c5d-aa00-ca776bd7f792/phe199-liver.pdf.aspx

- **Vaz et al. (2023) — NAFLD Prevalence in Australia**
  Measured prevalence 35-39%; clinical diagnosis rate ~6%. Sex trends.
  *Journal of Gastroenterology and Hepatology*. PMC10946623.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC10946623/

- **Hormones Australia — Hypothyroidism / Hyperthyroidism**
  Hypothyroidism ~3% (incl. subclinical), Hyperthyroidism ~0.3%. F>>M.
  https://www.hormones-australia.org.au/endocrine-diseases/hypothyroidism/
  https://www.hormones-australia.org.au/endocrine-diseases/hyperthyroidism/

- **PMC — Micronutrient Deficiencies and Anaemia in Australian Adults**
  Iron deficiency anaemia ~8-12% women reproductive age; <5% men.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9809261/

## SNOMED CT

- **CSIRO Ontoserver (FHIR R4)**
  Used to expand ECL expressions across multiple SNOMED CT-AU editions (2021-2026) for disease code set analysis.
  https://r4.ontoserver.csiro.au/fhir

- **CSIRO Ontoserver (Terminology Server)**
  Used for runtime SNOMED CT ECL expansion via FHIR ValueSet/$expand in the conditions module.
  https://tx.ontoserver.csiro.au/fhir