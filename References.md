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

## Lifestyle Factor Interactions

- **Athlete BMI Suppression Multiplier (0.33)**
  Athletes are significantly less likely to be overweight/obese than the general population. ABS National Health Survey 2022-23 reports ~65% of Australian adults as overweight or obese, while literature on athlete BMI across a general sport mix (NCAA, Olympic, professional) suggests ~20-25% of athletes exceed BMI 25. The 0.33 multiplier applied to general population high_bmi rates yields ~17-23% co-occurrence, consistent with:
  - Ode JJ et al. (2007) "Body mass index as a predictor of percent fat in college athletes and nonathletes." *Med Sci Sports Exerc.* 39(3):403-409.
  - Nevill AM et al. (2015) Olympic athlete BMI distributions by sport type.
  - ABS National Health Survey 2022-23: 65.8% of adults overweight or obese.
  https://www.abs.gov.au/statistics/health/health-conditions-and-risks/overweight-and-obesity/latest-release

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

## Injury Epidemiology

- **AIHW -- Injury in Australia (Body parts injured / Types of injury)**
  Limbs are the most commonly injured body region. Fractures of the shoulder or upper limb 36% of fractures (11,600 cases); hip or lower limb 23% (7,300 cases). Ages 15-24 have the highest hip and lower limb hospitalisation rate (145 per 100,000) and the highest fracture rate (235 per 100,000). Basis for the Limb Injury age bands and the secondary rise in older age groups.
  https://www.aihw.gov.au/reports/injury/injury-in-australia/contents/body-parts-injured

- **AIHW -- Sports Injury in Australia (Nature of injuries)**
  Sport is the most common specified setting for hospitalised fracture in males from mid-childhood into early adulthood (over 45% at ages 10-19, over 25% at ages 10-34). Basis for the band-level male skew applied to the Limb Injury 12-28 age range.
  https://www.aihw.gov.au/reports/sports-injury/sports-injury-in-australia/contents/nature-of-injuries

- **ABS -- Injury in Australia: A Snapshot (4825.0.55.001)**
  12% of the population (2.3 million people) sustained an injury in the previous four weeks; males 13%, females 11%. Basis for the Limb Injury base prevalence (0.030) and for treating overall sex distribution as near-even.
  https://www.abs.gov.au/ausstats/abs@.nsf/mf/4825.0.55.001

- **Safe Work Australia -- Key Work Health and Safety Statistics Australia**
  Serious work-related claims 2023-24: upper limb 33.2% (48,700 claims), lower limb 22.3% (32,700 claims), i.e. limbs account for ~55% of injuries. Used to scale total injury prevalence down to the limb subset.
  https://data.safeworkaustralia.gov.au/insights/key-whs-statistics-australia/latest-release

## Pregnancy Lab Parameters

- **HAPO Study Cooperative Research Group (2008) — Hyperglycemia and Adverse Pregnancy Outcomes**
  Fasting glucose distribution in 23,316 pregnant women: non-GDM mean 4.2 mmol/L, SD 0.4. Primary basis for Pregnancy condition glucose override (composite mean 4.4, SD 0.65 to include ~13% GDM subpopulation).
  *New England Journal of Medicine*. 2008;358(19):1991-2002.
  https://www.nejm.org/doi/full/10.1056/NEJMoa0707943

- **ADIPS 2014 Consensus Guidelines for GDM Testing and Diagnosis**
  Nankervis A, et al. Adopted IADPSG/WHO 2013 criteria for Australia: fasting glucose >= 5.1 mmol/L diagnostic for GDM.
  https://www.adips.org/downloads/2014ADIPSGDMGuidelinesV18.11.2014_000.pdf

- **AIHW — Diabetes in Pregnancy (2023)**
  ~16% of women who gave birth in Australian hospitals had GDM (2020-21). Rising trend from ~5% pre-2015 (partly due to lowered diagnostic thresholds).
  https://www.aihw.gov.au/reports/diabetes/diabetes-in-pregnancy

- **Crowther CA, et al. (2005) — ACHOIS Trial**
  Australian randomised trial of GDM treatment. Informed GDM fasting glucose distribution (mean ~5.5 mmol/L).
  *New England Journal of Medicine*. 2005;352(24):2477-2486.
  https://www.nejm.org/doi/full/10.1056/NEJMoa042973

## Infection Epidemiology

- **AIHW -- Infectious and Communicable Diseases**
  1.5M+ notifiable disease notifications in 2023. 362,600 infectious disease hospitalisations (2021), 92% non-notifiable. COVID-19 837k, influenza 290k, campylobacter 41k notifications.
  https://www.aihw.gov.au/reports/australias-health/infectious-and-communicable-diseases

- **NNDSS -- National Notifiable Diseases Surveillance System (Annual Reports)**
  Notification rates by age group: highest in children <5 (698/100k). Campylobacteriosis 93.5/100k, salmonellosis 55.3/100k, cryptosporidiosis 12.8/100k.
  https://www.cdc.gov.au/diseases/surveillance-systems-and-networks/national-notifiable-diseases-surveillance-system-nndss

- **Tham et al. (2022) -- Incidence of Acute Respiratory Infections in Australia**
  4-week ARI period prevalence 24.8%; ~68.9M cases/yr (~3.2/person/yr). Age 0-4: 46.3%, 65+: 9.7%. F 3.4 vs M 3.0/person/yr.
  *Communicable Diseases Intelligence*. PMC9151186.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9151186/

- **Vagenas et al. (2022) -- Sex and Gender Differences in Bacterial Infections**
  Males generally more susceptible; sepsis 55-64% male; legionellosis M:F 1.7-5; Q fever M:F ~1.6.
  *Infection and Immunity*. PMC9584217.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9584217/

- **RACGP -- Superficial Fungal Infections**
  Clinical guidance on tinea, candidiasis prevalence in Australian general practice. Onychomycosis up to 50% in >70yr.
  https://www1.racgp.org.au/getattachment/c11550b4-6687-4fcb-a89f-29fd3f9630cf/Superficial-fungal-infections.aspx

- **Slavin et al. (2017) -- Changing Epidemiology of Candidaemia in Australia**
  Mean annual incidence 2.41/100k population. C. albicans 44.4%, C. glabrata 26.7%.
  *Journal of Antimicrobial Chemotherapy*. 72(4):1103-1108.
  https://academic.oup.com/jac/article/72/4/1103/2514408

- **Kilburn et al. (1999) -- Prevalence of Tinea Pedis in Australian School Students**
  Age/sex-adjusted culture-proven prevalence 5.2%; increasing from 2.1% (4-6yr) to 9.7% (16-18yr).
  https://pubmed.ncbi.nlm.nih.gov/10354029/

- **Lim et al. (2015) -- Cryptosporidiosis in Australia: Tropical and Remote Areas**
  Notification rate 12.8/100k. Highest in warm, remote areas and Aboriginal/Torres Strait Islander populations.
  *PLoS Neglected Tropical Diseases*. PMC4579119.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4579119/

- **Moncrieff et al. (2022) -- Epidemiology of Notifiable Diseases in Australia 1991-2011**
  Other bacterial diseases notification incidence 9/100k/yr; 60% TB, 24% meningococcal, 15% legionellosis.
  *Communicable Diseases Intelligence*. PMC9150208.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9150208/

## Infection Lab Result Patterns

Clinical sources for lab parameter overrides in `laboratory/conditions.json` for infection conditions.

- **StatPearls — Leukocytosis**
  Bacterial infection: WBC 11-30 ×10^9/L, neutrophilic predominance (70-80%), left shift.
  https://www.ncbi.nlm.nih.gov/books/NBK560882/

- **StatPearls — Lymphocytosis**
  Viral infection: normal-low WBC with lymphocyte predominance (>40%).
  https://www.ncbi.nlm.nih.gov/books/NBK549819/

- **StatPearls — Eosinophilia**
  Parasitic (helminth) infection: eosinophilia is the hallmark finding. Mild >500/µL, moderate >1500/µL.
  https://www.ncbi.nlm.nih.gov/books/NBK560845/

- **PMC — Eosinophils in Helminth Infection**
  Tissue-invasive helminths drive marked eosinophilia via IL-5/IL-13.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC5048491/

- **PMC — Eosinophils in Fungal Diseases (Rosenberg et al.)**
  Eosinophilia in allergic fungal disease (ABPA); monocytosis characteristic of chronic fungal infection.
  https://jlb.onlinelibrary.wiley.com/doi/full/10.1002/JLB.4MR1117-473R

- **PMC — CRP Velocity: Differentiating Bacterial vs Viral Infection**
  Bacterial CRP median ~133 mg/L; viral CRP typically <40 mg/L. CRP >60 mg/L ~90% predictive of bacterial aetiology.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC9728869/

- **StatPearls — C-Reactive Protein**
  CRP >50 mg/L strongly suggests bacterial infection. Mild rise (10-40 mg/L) in viral infections.
  https://www.ncbi.nlm.nih.gov/books/NBK441843/

- **PMC — Thrombocytopenia in Viral Infections**
  Viral infections cause thrombocytopenia via marrow suppression, immune-mediated destruction, splenic sequestration.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC7924611/

- **PMC — Hypoalbuminemia as Acute-Phase Response**
  Albumin is a negative acute-phase reactant; mean ~32-33 g/L in sepsis. Predictor of severity.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC7379941/

- **ScienceDirect — Ferritin in Infectious Diseases**
  Ferritin rises as acute-phase reactant in all infection types. Hepcidin-mediated iron sequestration lowers serum iron and transferrin saturation.
  https://www.sciencedirect.com/science/article/pii/S2052297525000204

- **PMC — Hyponatremia in Critically Ill Patients**
  Hyponatremia (SIADH) in 28-40% of sepsis patients. Mean sodium ~136 mmol/L.
  https://pmc.ncbi.nlm.nih.gov/articles/PMC3943132/

- **AAFP — Evaluation of Leukocytosis**
  Differential diagnosis framework: neutrophilia (bacterial), lymphocytosis (viral), monocytosis (chronic/fungal), eosinophilia (parasitic/allergic).
  https://www.aafp.org/pubs/afp/issues/2015/1201/p1004.html

- **StatPearls — Liver Function Tests**
  Hepatotropic viruses cause hepatocellular injury (ALT/AST predominant); fungal infiltration causes cholestatic pattern (ALP predominant).
  https://www.ncbi.nlm.nih.gov/books/NBK482489/

## Medicine Prescriptions

Sources for condition-to-medicine mappings in `medicines/prescriptions.json`, aligned with Australian prescribing practices.

- **Australian Diabetes Society — Type 2 Diabetes Glycaemic Management Algorithm (June 2024)**
  Informed T2DM medicine categories and prescribing order (metformin first-line, SGLT2i, DPP-4i, GLP-1 RA).
  https://www.diabetessociety.com.au/guideline/australian-t2d-glycaemic-management-algorithm-june-2024/

- **PBS — Restriction Changes to Type 2 Diabetes Mellitus Medicines**
  PBS access criteria for SGLT2 inhibitors, GLP-1 receptor agonists.
  https://www.pbs.gov.au/info/reviews/pbs-restriction-changes-to-type-2-diabetes-mellitus-t2dm-medicines

- **Australian Prescriber — First-Line Medicines in the Treatment of Hypertension**
  ACE inhibitors, ARBs, CCBs, thiazide diuretics as first-line. Beta-blockers not first-line for uncomplicated HTN.
  https://australianprescriber.tg.org.au/articles/first-line-medicines-in-the-treatment-of-hypertension.html

- **Australian Prescriber — Managing Hypercholesterolaemia**
  Statin prescribing patterns, ezetimibe as adjunct, fibrates for triglycerides.
  https://australianprescriber.tg.org.au/articles/managing-hypercholesterolaemia.html

- **Heart Foundation — ACS Guideline 2025**
  Secondary prevention post-ACS: aspirin, statins, beta-blockers, ACEi.
  https://www.heartfoundation.org.au/for-professionals/acs-guideline

- **Australian Prescriber — Secondary Prevention of Acute Coronary Syndromes (2025)**
  Summary of antiplatelet, statin, and antihypertensive prescribing post-ACS.
  https://australianprescriber.tg.org.au/articles/secondary-prevention-of-acute-coronary-syndromes-a-summary-of-the-new-2025-Australian-guideline.html

- **PBS — Utilisation Analysis of PBS-Listed Heart Failure Medicines (2024)**
  ACEi/ARNI, beta-blocker, MRA, SGLT2i utilisation in HFrEF and HFpEF.
  https://www.pbs.gov.au/reviews/utilisation-analysis-of-pbs-listed-medicines-for-heart-fail/

- **NPS MedicineWise — Medicines for Chronic Kidney Disease: A Practical Guide**
  ACEi/ARB, SGLT2i (dapagliflozin), phosphate binders, EPO agents.
  https://www.nps.org.au/news/medicines-for-chronic-kidney-disease-a-practical-guide

- **COPD-X Guidelines**
  Stepwise bronchodilator therapy: SABA, LAMA, LABA, ICS combinations.
  https://copdx.org.au/

- **Australian Prescriber — Drugs for Chronic Obstructive Pulmonary Disease**
  Inhaler classes and prescribing patterns in Australian practice.
  https://australianprescriber.tg.org.au/articles/drugs-for-chronic-obstructive-pulmonary-disease.html

- **Australian Prescriber — Disease-Modifying Drugs in Adult Rheumatoid Arthritis**
  Methotrexate first-line, triple therapy, biologic DMARDs after csDMARD failure.
  https://australianprescriber.tg.org.au/articles/disease-modifying-drugs-in-adult-rheumatoid-arthritis.html

- **Australian Prescriber — Modern Management of Thyroid Replacement Therapy**
  Levothyroxine as near-universal treatment for hypothyroidism.
  https://australianprescriber.tg.org.au/articles/modern-management-of-thyroid-replacement-therapy.html

- **Australian Prescriber — Managing Medicines in Alcohol-Associated Liver Disease**
  Thiamine supplementation, lactulose, spironolactone, naltrexone/acamprosate.
  https://australianprescriber.tg.org.au/articles/managing-medicines-in-alcohol-associated-liver-disease-a-practical-review.html

- **Australian Prescriber — Correcting Iron Deficiency**
  Oral iron (ferrous sulfate/fumarate) first-line, IV ferric carboxymaltose if oral fails.
  https://australianprescriber.tg.org.au/articles/correcting-iron-deficiency-1.html

- **Therapeutic Guidelines — Antibiotic Prescribing Summary**
  Amoxicillin, flucloxacillin, cefalexin, doxycycline, roxithromycin, trimethoprim prescribing patterns.
  https://www.safetyandquality.gov.au/sites/default/files/2023-05/gpsummary_v15.pdf

- **Australian Prescriber — Systemic Antifungal Agents for Cutaneous Infections**
  Terbinafine and fluconazole as most utilised systemic antifungals in Australia.
  https://www.nps.org.au/australian-prescriber/articles/systemic-antifungal-agents-for-cutaneous-fungal-infections

- **Australian Prescriber — Managing Osteoarthritis**
  Paracetamol, topical and oral NSAIDs, PPI gastroprotection.
  https://australianprescriber.tg.org.au/articles/managing-osteoarthritis.html

- **Therapeutic Guidelines -- Acute Pain (Musculoskeletal Injury)**
  Stepped analgesia for acute limb injury: paracetamol and NSAIDs first-line, opioids as a short-course adjunct only. Basis for the Limb Injury prescribing probabilities and for keeping opioid categories in the minority.
  https://www.tg.org.au/

- **TGA — Removal of Prescribing Restrictions for Ivermectin (June 2023)**
  GP prescribing restored for scabies, strongyloides.
  https://www.tga.gov.au/news/media-releases/removal-prescribing-restrictions-ivermectin

## SNOMED CT

- **CSIRO Ontoserver (FHIR R4)**
  Used to expand ECL expressions across multiple SNOMED CT-AU editions (2021-2026) for disease code set analysis.
  https://r4.ontoserver.csiro.au/fhir

- **CSIRO Ontoserver (Terminology Server)**
  Used for runtime SNOMED CT ECL expansion via FHIR ValueSet/$expand in the conditions module.
  https://tx.ontoserver.csiro.au/fhir

- **SNOMED CT Expression Constraint Language — 6.11 History Supplements**
  Defines the `{{ + HISTORY-MIN | HISTORY-MOD | HISTORY-MAX }}` syntax and the historical association reference sets each profile follows (MIN: `SAME AS`; MOD: adds `REPLACED BY`, `WAS A`, `PARTIALLY EQUIVALENT TO`; MAX: all). Basis for the concept-recovery measurements in `data-golf/analyse.py` and `data-golf/TerminologyDrift.md`.
  https://docs.snomed.org/snomed-ct-specifications/snomed-ct-expression-constraint-language/behaviour-specification-with-examples/6.11-history-supplements