# Data Golf 2026 — Kaggle Competition Copy

**Subtitle:** Score clinical questions against SNOMED CT-coded synthetic patient data.

## Overview

**Data Golf** is a free, educational competition about clinical terminology analytics. You work with synthetic patient encounters coded in SNOMED CT, and answer 18 yes/no clinical questions for each encounter.

### Goal

Your goal is to answer 18 yes/no clinical questions for each of about 256,000 synthetic patient encounters. You do this by querying the coded data with FHIR terminology services and ECL. We score your submission by comparing your answers to the correct answers.

The competition tests how well you can query coded health data using FHIR terminology services and the Expression Constraint Language (ECL). It rewards accuracy, not speed — and different valid approaches can produce different answers. That variation is part of the point.

Your host is Matt Cordell, in his role at CSIRO.

---

## Description

### What you're doing

You will receive **TrainingDataSet.csv**, a set of about 256,000 synthetic patient encounters spanning six years (2021–2026). Each row is one encounter, with:

- **Demographics** — sex, date of birth, state, and physical measurements.
- **A coded clinical note** — a SNOMED CT concept and its display text.
- **Up to three coded medicines** — SNOMED CT or AMT product concepts and their display text.
- **Laboratory results** — values from panels such as full blood count, lipids, thyroid function, and kidney function.

For every encounter, you must answer 18 questions (Q1–Q18). Each question states a criterion. Your answer is **True** if the criterion holds for that encounter, and **False** if it does not. See the [Questions](#questions) section below for the full list.

### Why the data changes over time

The dataset spans six SNOMED CT-AU editions (2021 to 2026), and the medicine coding model changes partway through:

- **Encounters before 2025** use SNOMED CT drug concepts.
- **Encounters from 2025 onward** use AMT product concepts.

Both models share the same underlying attributes, so you can query them consistently:

- **Has ingredient** (`<<762951001`, including active and precise active ingredient variants) — points to a substance (`<<105590001`).
- **Has basis of strength substance** (`732943007`) — also points to a substance.
- **Has manufactured dose form** (`411116001`).

All other SNOMED CT content in the dataset follows the international concept model. No other medicine-model differences matter for this competition.

Because each year uses a different SNOMED CT-AU edition, an ECL expression can match a different set of concepts depending on the year. Answer each encounter using the edition that was current on its `EncounterDate` — this is intentional, and working out how to handle it is part of the challenge.

### A note on the Age field

We do not publish `Age` directly. Work it out from `DateOfBirth` and `EncounterDate`. Only `DateOfBirth` appears in the dataset.

### Tools you can use

- **FHIR terminology services** (recommended) — query Ontoserver using ECL against the SNOMED CT-AU edition relevant to each encounter.
- **RF2 files** (alternative) — register with the [National Clinical Terminology Service (NCTS)](https://www.healthterminologies.gov.au/), download the latest "FULL" release, and identify edition states yourself.

You may use any programming language, library, or notebook environment to build your solution.

---

## Evaluation

We score submissions using **macro-F1** across all 18 questions. This means we calculate the F1 score for each question separately, then average the 18 scores. Every question counts equally, regardless of how common a "True" answer is for that question.

### Submission format

Submit a CSV with one row per episode and one column per question:

```
Episode Number,Q1,Q2,Q3,...,Q18
1,True,False,True,...,False
2,False,False,False,...,True
```

Use `sample_submission.csv` as a template.

---

## Timeline

- **26 August 2026** — Competition opens.
- **27 September 2026, 11:59 PM AEST** — Submission deadline.
- **SNOMED CT 2026 Expo (Sydney)** — We announce results and present an analysis of participants' approaches.
- **After the Expo** — We publish results on the competition page.

---

## Prizes

Data Golf is a free, educational competition. Any prize we offer has no monetary value and exists purely for fun. We may ask the winner to share their real name, but they are under no obligation to do so.

---

## Rules

You must follow these rules to take part:

- **Use the published files only.** Answer every question using columns available in `TrainingDataSet.csv`. Do not attempt to reconstruct withheld fields.
- **Submit one row per episode.** Your submission must cover every `Episode Number` in the training set.
- **Work individually or in a team**, as permitted by the standard Kaggle competition rules.
- **Complete the post-competition survey.** We will ask all participants for feedback on the competition after it closes.

---

## Privacy

The dataset contains **synthetic patient data only** — it does not describe real people. Participant privacy works as follows:

- We will not share your personal data with any party outside this competition and its associated Expo presentation.
- We will not include anything that identifies you in the Expo presentation.
- If you win, we may ask for your real name, but you may decline.

---

## Data Access and Use

[*Competition Use and Non-Commercial & Academic Research is checked*: You may access and use the Competition Data for non-commercial purposes only, including for participating in the Competition and on Kaggle.com forums, and for academic research and education. The Competition Sponsor reserves the right to disqualify any Participant who uses the Competition Data other than as permitted by the Competition Website and these Rules.]

We also license the Competition Data under the **MIT License**. This means you may additionally use, copy, modify, and share the Competition Data — including for commercial purposes — as long as you keep the MIT License's copyright and permission notice with any copy you distribute.

If the two terms above conflict for a specific use, the **MIT License governs**, since it grants the broader permissions.

---

## External Data and Tools, Eligibility, Winner's Obligations, and Governing Law

### 6. External data and tools

- **You may use external data and tools.** You may use any data, software, or tool beyond the Competition Data to build your submission, including commercial and paid tools.
- **We place no cost or licensing restriction on your choices.** Because Data Golf offers no monetary prize, we do not apply Kaggle's standard "reasonable cost" test to external data or tools. Use whatever you would normally use for this kind of analysis.
- **You may use automated machine learning tools (AMLT).** If you use an AMLT (for example, Google AutoML or H2O Driverless AI), you must hold a valid license for it.
- **The goal is to compare methods, not restrict them.** We designed Data Golf so you can analyse the data with your own normal tools and methods. Part of the value of the competition is comparing how different tools and approaches perform against the same questions.

### 7. Eligibility

- **CSIRO employees may enter.** Employees, interns, contractors, officers, and directors of CSIRO and Kaggle Inc. may enter and participate, but they are not eligible to win the competition's prize.
- **Your employer's policies still apply.** If you work for CSIRO or Kaggle Inc., your participation is also subject to your employer's internal policies.

### 8. Winner's obligations

Because Data Golf's prize has no monetary value, we ask less of the winner than Kaggle's standard rules require:

- **The winner must share their method.** You must describe the tools, data sources, and approach you used to produce your winning submission, in enough detail for us to understand how you reached your answers.
- **The winner may be asked for their real name**, as described under [Prizes](#prizes). You are not obliged to provide it.
- **We do not require tax forms or a commercial license grant.** Because no monetary prize is involved, Kaggle's standard requirements for prize acceptance documents and IP licensing do not apply.

### 9. Governing law

- **California law governs these rules.** Unless the Competition-Specific Rules state otherwise, disputes about these rules are governed by California law, without regard to its conflict-of-laws rules.
- **Santa Clara County courts have exclusive jurisdiction.** You and CSIRO both consent to the personal jurisdiction of the Federal and State courts of Santa Clara County, California, USA.
- **The remaining rules stay in force.** If a court finds one part of these rules invalid or unenforceable, every other part remains in effect.

---

## Data description (files)

| File | Contents | Notes |
|---|---|---|
| `TrainingDataSet.csv` | Demographics, labs, coded clinical note, coded medicines. | Your main input file. |
| `sample_submission.csv` | Example submission format, filled with random answers. | Use this as your template. |

---

## Columns

*   `Episode Number` - a unique identifier for the encounter. Use this to key your submission rows.
*   `EncounterDate` - the date of the encounter. Use it to work out which SNOMED CT-AU edition applies, and to derive the patient's age at the encounter.
*   `DateOfBirth` - the patient's date of birth. Use it with `EncounterDate` to derive age; we do not publish age directly.
*   `Sex` - the patient's recorded sex (`male` or `female`).
*   `State` - the Australian state or territory of the encounter.
*   `Height_cm` - the patient's height, in centimetres.
*   `Weight_kg` - the patient's weight, in kilograms.
*   `GivenName`, `FamilyName`, `StreetAddress`, `City`, `Postcode` - synthetic identity and address details generated for realism. These do not identify a real person.
*   `Clinical_Note_Code` - the SNOMED CT concept ID recorded for the encounter's clinical note.
*   `Clinical_Note_Display` - the display text (preferred term) for `Clinical_Note_Code`.
*   `Medicine_1_Code`, `Medicine_2_Code`, `Medicine_3_Code` - the SNOMED CT or AMT product concept ID for each medicine prescribed at the encounter. A patient may have zero, one, two, or three medicines recorded.
*   `Medicine_1_Display`, `Medicine_2_Display`, `Medicine_3_Display` - the display text for the matching `Medicine_*_Code` column.
*   Remaining columns - laboratory results across panels such as full blood count, lipids, thyroid function, kidney function, iron studies, and inflammatory markers, etc.

---

## Questions

| # | Criterion |
|---|---|
| Q1 | Patients with female as their recorded sex. |
| Q2 | Patients with a BMI of 30 or more and a total cholesterol to HDL ratio greater than 5. |
| Q3 | Patients documented as being healthy or free of current problems. |
| Q4 | Patients with hyperthyroidism according to their clinical note. |
| Q5 | Patients with osteoarthritis in 2024. |
| Q6 | Patients taking an ACE inhibitor. |
| Q7 | Patients taking a product containing a cardiac (digitalis) glycoside. |
| Q8 | Patients with a fungal foot infection. |
| Q9 | Patients taking more than one product that contains paracetamol. |
| Q10 | Patients with a bilateral condition. |
| Q11 | Female patients aged 15 to 49 taking methotrexate. |
| Q12 | Pregnant patients prescribed a teratogenic medicine. |
| Q13 | Patients with osteoarthritis or rheumatoid arthritis taking an oral NSAID, and their eGFR is below 60. |
| Q14 | Patients with an open wound on an upper limb, excluding the fingers and thumb. |
| Q15 | Pregnant patients with a fasting glucose of 5.1 mmol/L or greater. |
| Q16 | Patients with a non-Streptococcal bacterial joint infection. |
| Q17 | Patients taking an oral iron supplement. |
| Q18 | Patients taking a mineral supplement, excluding the electrolytes sodium, potassium, or chloride. |

---

## Open items to confirm

- **Timezone** for the deadline — assumed AEST (Sydney-based Expo).
- **Kaggle standard rules** (team size limits, external data policy, etc.) — not drafted here; say if you want this section added.
