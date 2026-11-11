# Data Golf 2026: why each question was chosen

Each of the 18 questions was picked to test one or more specific skills in
working with SNOMED CT and the Expression Constraint Language (ECL).
This page gives the reason for each question, the skill it tests and how
hard we expected it to be.

**Difficulty scale:** 1 (easiest) to 6 (hardest). These are the organiser's
expectations before the event, not measured results.

**True counts** come from the answer key for the 279,912 episodes in the
competition dataset.

## Summary

| Q | Criterion | Main skill tested | Difficulty | True count |
|---|-----------|-------------------|:----------:|-----------:|
| Q1 | Female as recorded sex | Basic lookup | 1 | 139,606 |
| Q2 | BMI 30 or more and cholesterol:HDL ratio above 5 | Data wrangling, no SNOMED CT | 2 | 45,542 |
| Q3 | Healthy or free of current problems | First ECL; a concept outside the obvious hierarchy | 2 | 15,731 |
| Q4 | Hyperthyroidism according to the clinical note | Edition drift; a 2022 hierarchy change; precision | 4 | 10,859 |
| Q5 | Osteoarthritis in 2024 | Large edition drift | 3 | 3,819 |
| Q6 | Taking an ACE inhibitor | Drug class inferred through ingredients | 3 | 9,059 |
| Q7 | Taking a cardiac (digitalis) glycoside | Drug class inferred through ingredients | 3 | 239 |
| Q8 | Fungal foot infection | Composing an ECL where no single concept exists | 3 | 179 |
| Q9 | More than one product containing paracetamol | Counting across medicine columns | 4 | 3,230 |
| Q10 | Bilateral condition | Complex ECL with left and right finding sites | 4 | 7,038 |
| Q11 | Female, aged 15 to 49, taking methotrexate | Multiple criteria with calculated age | 4 | 2,250 |
| Q12 | Pregnant and prescribed a teratogenic medicine | Pregnancy identification and a self-built drug list | 6 | 347 |
| Q13 | OA or RA, oral NSAID, eGFR below 60 | Drift, complex ECL and dose form | 4 | 1,819 |
| Q14 | Open wound on upper limb, excluding fingers and thumb | ECL using the anatomy hierarchy | 3 | 22,600 |
| Q15 | Pregnant with fasting glucose of 5.1 mmol/L or more | Pregnancy identification plus a lab value | 4 | 461 |
| Q16 | Non-Streptococcal bacterial joint infection | Attributes combined with subtraction | 3 | 1,472 |
| Q17 | Taking an oral iron supplement | Substance grouper and dose form | 3 | 10,649 |
| Q18 | Taking a mineral supplement, excluding sodium, potassium, chloride | Building your own enumerated list | 5 | 14,498 |

## How the questions and data were shaped

Two kinds of evidence shaped the question set. The dataset was also tuned so
that terminology change would have a visible effect on the answers.

**1. Comparing ECL results across editions.** Before choosing the final
questions, we expanded candidate ECLs against each of the six editions and
flagged those whose member count moved by 20% or more. These early ECLs were
preliminary and differ from the final ones, but they showed where the
terminology was unstable:

| Candidate criterion | Members, 2021 to 2026 editions | Spread | Question |
|---|---|---|---|
| Hyperthyroidism | 67, 21, 21, 22, 23, 26 | 69% | Q4 |
| Bilateral condition | 1,147 up to 2,833 | 60% | Q10 |
| Pregnancy | 1,602, 1,258, 775, 1,314, 1,266, 1,232 | 52% | Q12, Q15 |
| Rheumatoid arthritis | 60 up to 114 | 51% | Q13 |
| Osteoarthritis | 294 up to 350, then 181 | 48% | Q5, Q13 |
| Non-Streptococcal bacterial joint infection | 69 up to 106 | 35% | Q16 |
| Methotrexate products (2021 to 2024 model) | 9, 9, 4, 6 | 56% | Q11 |

The 69% drop for hyperthyroidism between the 2021 and 2022 editions is the
*Thyrotoxicosis* change described under Q4.

The comparison also showed that the product model changes in 2025. The count of
*Medicinal product* concepts grows about 6.6 times (25,306 to 166,511) as AMT
trade products arrive. Some medicine criteria go the other way. Cardiac
glycoside products fall from 16 to 7, which matters for Q7.

**2. Natural terminology drift, especially retired concepts.** Concepts are
retired between editions, and a code recorded in 2021 may be inactive by 2026.
With random code selection, some questions had almost no True rows, so the
concepts behind them were rarely drawn and few ever became inactive. The
generator therefore raises their frequency:
- A list of in-scope concepts that were retired with no historical association
  is over-sampled at three times the weight of their peers. A history supplement
  cannot recover these concepts, so they make the drift show up in the answers.
- A second setting favours codes that are active at the encounter but inactive
  in the July 2026 edition.

The effect is large. In the final dataset, for example, 2,747 of the 3,819
positive rows for Q5 and 12,042 of the 22,600 positive rows for Q14 are matched
by a code that is inactive in the July 2026 edition. Five questions (Q5, Q10,
Q13, Q14 and Q15) have between half and three-quarters of their positives in
this position. These shares come from seeding, so they are not natural
retirement rates.

The drift analysis separates two effects. **Retirement** removes a code, and a
history supplement can recover it only if SNOMED International recorded a
historical association. **Reclassification** moves a concept that is still active
out of a subtree, and no history supplement can recover that. In the final data,
retirement without an association accounts for most of the loss in Q5 and Q13,
and reclassification accounts for all of the loss in Q4. Either way, answering
with the latest edition gives a different answer from the encounter-time edition.

## Warm-up questions (Q1 to Q3)

**Q1: Female as recorded sex.** A warm-up. The `Sex` column holds one of three
values (male, female, non-binary), so the answer is unambiguous. No
terminology is needed. It confirms that participants can read the file and
submit in the right format.

**Q2: BMI of 30 or more and total cholesterol to HDL ratio above 5.** Slightly
harder, but still no SNOMED CT knowledge. Participants must work out BMI from
height and weight, and the ratio from two laboratory columns. The cholesterol
value comes from the lipid panel, or from another panel when the lipid panel is
missing.

**Q3: Healthy or free of current problems.** The first introduction to ECL.
SNOMED CT has a *Healthy* hierarchy, but a patient may instead be recorded
with *No current problems or disability*. That concept is not a subtype of
*Healthy*, so a query on *Healthy* alone misses rows. Asking for "anything that
is not a Disease" would also be wrong, because many finding concepts imply that
the patient has a condition.

## Terminology drift (Q4, Q5)

The dataset spans six SNOMED CT-AU editions, and each encounter is answered
against the edition current on its date. These questions show how much that
matters.

**Q4: Hyperthyroidism according to the clinical note.** The main reason for this
question is a structural change in the 2022 update: *Thyrotoxicosis (disorder)*
(90739004) stopped being a subtype of *Hyperthyroidism (disorder)* (34486009).
Participants who use the 2021 edition for the 2021 cohort get a different
answer from those who use a later edition. The laboratory results should align
with the diagnosis codes, but not every coded diagnosis is formally
hyperthyroidism. SNOMED CT still holds concepts that do not meet the formal
definition, so a precise answer needs careful research.

**Q5: Osteoarthritis in 2024.** A large, deliberate example of drift. The
*Osteoarthritis* subtree changed substantially between editions, for example from
431 concepts in 2025 to 181 in 2026. Using the latest edition gives a very
different answer from the edition current in 2024. The question also asks
participants to handle the calendar year against editions that run February to
January. The edge case is there to keep the question simple, not as a trick.

## Drug classes reached through ingredients (Q6, Q7, Q17)

SNOMED CT has no concept such as "ACE inhibitor product" that groups products
directly. Participants must go through the ingredient attributes. The data also
switches product model partway through: international clinical drugs before
2025, and AMT products from 2025.

**Q6: Taking an ACE inhibitor.** The class is reached through its ingredients.
Fixed-dose combination products count.

**Q7: Taking a product containing a cardiac (digitalis) glycoside.** The same
skill as Q6. The low number of True rows is a side effect of the data, not the
aim of the question. The edition comparison also showed that matching products
shrink from 16 to 7 at the 2025 product-model change, so the question tests
both model eras.

**Q17: Taking an oral iron supplement.** Participants need the grouper
*Product containing iron and/or iron compound* (768459000), not *Product
containing iron (medicinal product)* (30729008). SNOMED CT has no "is
modification of" relationship between a chemical element and its clinical salts
and compounds, so the element-level concept misses the compounds actually
prescribed. The question also needs the dose form to separate oral products from
injectable iron.

## Composing an ECL (Q8, Q10, Q14, Q16)

**Q8: Fungal foot infection.** No single concept describes this group.
Participants had to compose one from existing concepts, such as *Mycosis* and
*Infection of foot*.

**Q10: Bilateral condition.** SNOMED CT has no "bilateral" flag. The reference ECL
looks for findings with one finding site on the left and another on the right.
It needs a complex expression. A text search can serve as a backup for concepts
that are under-modelled.

**Q14: Open wound on an upper limb, excluding the fingers and thumb.** Tests an ECL
that uses the anatomy hierarchy: find open wounds in the upper limb, then
subtract the digits.

**Q16: Non-Streptococcal bacterial joint infection.** Combines attributes (a
bacterial causative agent and a joint finding site) with subtraction of the
streptococcal causes. Using *Causative agent* means "caused by" rather than
"mentions a bacterium in any role", which a text search would not separate.

## Safety questions that combine several criteria (Q9, Q11, Q12, Q13, Q15)

These questions mirror real medicine-safety checks.

**Q9: More than one product containing paracetamol.** A patient can be on more
than one medicine that contains paracetamol, which is a real safety concern.
Participants must count matching products across all three medicine columns,
including combination products.

**Q11: Female patients aged 15 to 49 taking methotrexate.** The first
multi-criteria question. The ECL is simple (`<68887009 |Product containing
methotrexate|` is enough). The challenge is combining sex, an age calculated
from date of birth and encounter date, and the medicine.

**Q12: Pregnant patients prescribed a teratogenic medicine.** The hardest question,
with two difficult parts.
- *Identifying pregnant patients* is not a simple ECL. There is a finding
  *Pregnancy* (77386006), but participants must decide how to treat ectopic
  pregnancy, exclude birth and history of pregnancy, exclude postnatal and
  puerperal states, and consider co-morbidities that imply pregnancy.
- *Identifying teratogens.* SNOMED CT has a concept for this (45986006), but it
  has no subtypes, so using it returns no products. Participants must build their
  own list of substances. The reference list was chosen after comparing a number
  of sources.

**Q13: OA or RA, taking an oral NSAID, with eGFR below 60.** Combines terminology
drift (it shares the osteoarthritis hierarchy with Q5) with a complex ECL. The
new element is the dose form: participants must keep oral products and drop
topical ones. Aspirin counts as an NSAID.

**Q15: Pregnant patients with fasting glucose of 5.1 mmol/L or more.** Pregnancy
identification again, now with a laboratory threshold. Identifying the pregnant
patients is the hardest part.

## Building your own list (Q18)

**Q18: Taking a mineral supplement, excluding sodium, potassium and chloride.**
SNOMED CT contains *Mineral supplement (substance)* (373460003). It has a
reasonable number of children, so it looks like a good answer, but none of them
are substances that products actually use. Participants must research and
enumerate their own list. The wording follows the ATC group A12, *Mineral
supplements*, but the phrase is ambiguous and open to interpretation. ATC itself
classifies iron elsewhere. Minerals are usually described by their elements, so
they also hit the missing "is modification of" relationship described under
Q17. We expect, and accept, variation between submissions on this question.

## Why the set has 18 questions

Eighteen holes in a round of golf. The number is as good as any other, and it
stopped the scope from growing. The set was cut down from an earlier
37-question draft. Questions that depended on withheld columns, or that tested
general data skills rather than terminology, were dropped. The earlier
questions remain in the repository's git history.
