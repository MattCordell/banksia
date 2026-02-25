# Contraindications Reference

Identified contraindications across the conditions, medicines, and lab tests in this synthetic data generator. Organised by category. Some are detectable in the current single-condition model via lab values; others become relevant when multimorbidity is added.

---

## 1. Lab-Driven: Metformin in Reduced eGFR (T2DM)

**Conditions involved:** Type 2 Diabetes Mellitus
**Medicines involved:** Metformin / Biguanide (`<1363127000`) — assigned at 85% probability
**Lab signals:** `Creatinine (µmol/L)`, `eGFR (mL/min/1.73m²)` (MBAP / Kidney Function panels)

T2DM generates creatinine with a lognormal distribution (mean 110 µmol/L, SD 55). Some patients land in the upper tail with creatinine > 200–300 µmol/L and eGFR < 30 mL/min/1.73m², yet Metformin is still assigned unconditionally at 85%.

| eGFR threshold | Clinical guidance |
|---|---|
| < 45 mL/min/1.73m² | Dose reduction required |
| < 30 mL/min/1.73m² | **Absolute contraindication** — lactic acidosis risk |

**Also applies to:** SGLT2 inhibitors (35% for T2DM) — ineffective and contraindicated below eGFR ~25 mL/min/1.73m².

---

## 2. Lab-Driven: Digoxin in Heart Failure with Severe Renal Impairment

**Conditions involved:** Heart Failure (Chronic)
**Medicines involved:** Digoxin (`387461009`) — assigned at 15% probability
**Lab signals:** `Creatinine (µmol/L)`, `eGFR (mL/min/1.73m²)`, `Potassium (mmol/L)`

Heart Failure generates creatinine with mean 140 µmol/L, SD 100 (lognormal), so a meaningful fraction of HF patients will have eGFR < 30. Digoxin is renally cleared and has a narrow therapeutic index — levels just above therapeutic cause toxicity (bradycardia, arrhythmias). Dose must be halved or drug avoided entirely in significant CKD.

Compounding risk: HF patients also receive **loop diuretics at 65%**, which deplete potassium. Hypokalaemia potentiates digoxin toxicity, making the combination of low eGFR + loop diuretics + digoxin particularly hazardous.

---

## 3. Demographic: Teratogenic Medicines in Females of Reproductive Age

No age or sex guard exists on medicine assignment. Several medicines assigned at high probability are category D or X teratogens.

| Condition | Medicine | Probability | Teratogen risk |
|---|---|---|---|
| Essential Hypertension / IHD / CKD | ACE inhibitors (`<372733002`) | 45–70% | Category D — fetal renal dysgenesis and oligohydramnios |
| Essential Hypertension | ARBs (`<372913009`) | 30% | Category D — same mechanism as ACEi |
| Rheumatoid Arthritis | Methotrexate (`387381009`) | 70% | Category X — abortifacient and teratogen |
| Bacterial Infection | Tetracyclines / Doxycycline (`<373206009`) | 15% | Category D — fetal teeth and bone development |
| Hyperthyroidism | Carbimazole (within antithyroid ECL `<418416001`) | 80% | Teratogenic — PTU preferred in first trimester |

**Example:** A 28-year-old female with Essential Hypertension will receive ramipril or irbesartan at high probability — a standard clinical safety flag in practice.

**Reproductive age window to check:** approximately 15–49 years, female sex.

---

## 4. Duplicate and Conflicting Medicines

### 4a. Within-condition: Paracetamol + NSAID co-prescription (Osteoarthritis)

**Condition:** Osteoarthritis
**Medicines:** Non-opioid analgesic (paracetamol, 50%) + Oral NSAIDs (ibuprofen/naproxen/celecoxib, 40%)

Both slots are independent rolls, so approximately 20% of OA patients receive both concurrently. While clinically manageable (PPI is also in the list at 25% for gastroprotection), if the non-opioid ECL resolves to a compound paracetamol product (e.g., paracetamol + codeine), the patient could unknowingly receive a double paracetamol dose exceeding safe daily limits.

### 4b. Cross-condition duplicates (relevant on multimorbidity)

Several ECLs are shared across conditions with no deduplication. A patient with two conditions drawing from the same class will receive the same drug class twice as separate prescriptions.

| Medicine class | ECL | Conditions that prescribe it |
|---|---|---|
| Statins | `<372912004` | T2DM (60%), Hyperlipidaemia (90%), IHD (90%), CKD (50%), NAFLD (40%) |
| ACE Inhibitors | `<372733002` | HTN (45%), IHD (55%), HF (50%), CKD (70%), NAFLD (25%) |
| Metformin | `<1363127000` | T2DM (85%), NAFLD (30%) |
| Loop Diuretics | `<372691009` | Cirrhosis (35%), CKD (40%), HF (65%) |
| SGLT2 Inhibitors | `<703673007` | T2DM (35%), HF (40%), CKD (35%) |
| Oral NSAIDs | `<372665008` | Osteoarthritis (40%), Rheumatoid Arthritis (35%) |
| Non-opioid analgesics | `<373216001` | Healthy (8%), Viral Infection (60%), Osteoarthritis (50%) |

**Examples:** T2DM + Hyperlipidaemia → duplicate statin; T2DM + NAFLD → duplicate Metformin; Osteoarthritis + Viral Infection → duplicate paracetamol prescription.

---

## 5. Cross-Condition: NSAIDs in Kidney Disease or Heart Failure

**Medicines involved:** Oral NSAIDs (`<372665008`) — prescribed for Osteoarthritis (40%) and Rheumatoid Arthritis (35%)
**Contraindicated in:** Chronic Kidney Disease (Stage 3–4), Heart Failure (Chronic)
**Lab signals:** elevated `Creatinine (µmol/L)`, reduced `eGFR (mL/min/1.73m²)`, low `Sodium (mmol/L)` (HF mean 133 mmol/L)

NSAIDs reduce renal prostaglandin synthesis → decreased renal blood flow → risk of acute kidney injury on top of CKD. In heart failure, NSAIDs cause sodium and water retention, worsening congestion and reducing the effect of diuretics.

A patient with Osteoarthritis + CKD (or OA + HF) receiving NSAIDs is a textbook medication safety case. All lab signals to detect this are already available in the generator.

---

## 6. Cross-Condition: Non-Selective Beta-Blockers in COPD

**Condition prescribing the medicine:** Chronic Liver Disease / Cirrhosis
**Medicine:** Non-selective beta-blockers (`<373254001 AND <441338003`) — propranolol or carvedilol, prescribed at 65% for variceal prophylaxis
**Contraindicated in:** COPD

Non-selective beta-blockade causes bronchoconstriction by blocking β2 receptors in bronchial smooth muscle. Cardioselective β1-blockers (bisoprolol, metoprolol) are the safer alternative in patients with airways disease. A patient with both cirrhosis and COPD would receive a clinically problematic medicine.

**Lab signals:** COPD generates elevated WBC (mean 9.5 ×10⁹/L) and CRP (mean 25 mg/L), which together with the condition label would identify the problematic combination.

---

## Summary

| # | Contraindication | Signal type | Detectable in current model? |
|---|---|---|---|
| 1 | Metformin + eGFR < 30 (T2DM) | Lab value | **Yes** |
| 1b | SGLT2 inhibitors + eGFR < 25 (T2DM) | Lab value | **Yes** |
| 2 | Digoxin + low eGFR + loop diuretics (HF) | Lab value + medicine | **Yes** |
| 3 | ACEi / ARB / Methotrexate / Doxycycline + female reproductive age | Demographics | **Yes** |
| 4a | Paracetamol compound duplication (OA concurrent prescriptions) | Overlapping ECL | **Possible now** |
| 4b | Statin / ACEi / Metformin / NSAID duplication across conditions | Cross-condition ECL | On multimorbidity |
| 5 | NSAIDs + CKD or Heart Failure | Cross-condition + lab | On multimorbidity |
| 6 | Non-selective beta-blockers + COPD | Cross-condition | On multimorbidity |

---

## Implementation Notes

- **Guard rails:** Contraindications 1 and 2 could be implemented in `medicines/generator.py` by comparing the generated eGFR against thresholds before assigning certain medicines.
- **Demographic filtering:** Contraindication 3 could use the existing sex/age fields on `PatientContext` to exclude or flag teratogenic medicines for females within a reproductive age range, similar to the existing SNOMED exclusion pattern in `conditions/generator.py`.
- **Deduplication:** Contraindication 4b would require a deduplication step in `generate_medicines()` when multimorbidity is introduced, comparing ECL expressions or resolved SNOMED codes across all assigned medicine slots.
- **Cross-condition flags:** Contraindications 5 and 6 require the `PatientContext.condition` field (or a future `conditions: List[str]` field) to hold multiple conditions before they can be enforced.
