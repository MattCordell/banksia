# Terminology drift and its impact on analytics

Findings from measuring how SNOMED CT-AU edition changes affect the Data Golf
answer set. Measured 2026-08-28 against the 279,912-row competition dataset.
Encounters span six editions (20210131 - 20260131). The reference edition is
20260731.

Reproduce with `python data-golf/analyse.py --reference-edition 20260731`. The
numbers land in the `INACTIVE CONCEPTS`, `INACTIVE CONCEPTS IN QUESTION SCOPE`
and `EFFECT OF RECOMPUTING AGAINST ...` sections of `metrics.txt`. The
retirement-versus-reclassification split in Finding 2 comes from a separate
check, described under Method.

An earlier version of this document measured a first, unseeded run of 256,515
rows. It is in the git history. Where its conclusions differ from this one, the
text says so.

## The question this answers

An analytics query written against a coded dataset has to resolve its value sets
against *some* edition of the terminology. There are two defensible choices:

1. **The latest edition**, on the assumption that later releases are
   improvements, using ECL history supplements to reach concepts retired since
   the data was recorded.
2. **The edition current at the time of the encounter**, which sidesteps missing
   historical associations but queries a hierarchy that may since have been
   corrected.

`analyse.py` uses **option 2**. Each row is mapped to its encounter edition and
every ECL is expanded once per edition, so a flag reflects the terminology active
when the encounter happened.

The obvious risk of option 2 is stale hierarchies. The obvious risk of option 1
is that SNOMED International sometimes retires a concept without a historical
association, leaving nothing for a supplement to follow. We measured both.

## How the dataset was seeded

**The retirement figures below describe a dataset built to show drift. They are
not natural retirement rates.**

With random code selection, some questions had almost no True rows, so the
concepts that decide them were rarely drawn and few of them ever became
inactive. The generator therefore applies two biases:

- **A boost list** (`boost_codes.json`). It names in-scope concepts that are
  inactive by the reference edition and have no historical association, so no
  history supplement can recover them. These concepts are drawn at three times
  the weight of their peers.
- **An inactive-rate bias** (`--inactive-rate`). With this probability, a code
  draw favours concepts that are active in the encounter's edition but inactive
  in 20260731.

The result: 967 of 21,210 distinct concepts (4.6%) are inactive in 20260731,
but 136,756 of 279,912 clinical-note rows (48.9%) carry one. The medicine
columns are lower, at 12.7% to 21.8% of populated rows.

## Finding 1: retirement is large by design, and mostly recoverable

Of the 967 inactive concepts, **280 fall inside a question's ECLs**. The rest
are drift in codes no criterion refers to, and are harmless. **78 of the 280
have no historical association** and cannot be recovered by any profile.

| Q | in scope, inactive | MIN | MOD | MAX | unrecoverable | positives | positives on an inactive code |
|---|---|---|---|---|---|---|---|
| Q5 osteoarthritis in 2024 | 8 | 3 | 4 | 4 | 4 | 3,819 | 2,747 |
| Q6 ACE inhibitor | 16 | 0 | 15 | 16 | 0 | 9,059 | 2,214 |
| Q10 bilateral condition | 10 | 1 | 9 | 10 | 0 | 7,038 | 4,242 |
| Q11 F 15-49 on methotrexate | 4 | 0 | 4 | 4 | 0 | 2,250 | 526 |
| Q12 pregnant on teratogen | 194 | 4 | 113 | 124 | 70 | 347 | 76 |
| Q13 OA/RA, NSAID, low eGFR | 34 | 15 | 25 | 27 | 7 | 1,819 | 1,222 |
| Q14 open wound, upper limb | 41 | 1 | 28 | 40 | 1 | 22,600 | 12,042 |
| Q15 pregnant, high glucose | 147 | 4 | 72 | 82 | 65 | 461 | 231 |
| Q16 non-Strep joint infection | 1 | 0 | 0 | 1 | 0 | 1,472 | 380 |
| Q18 mineral supplement | 2 | 0 | 2 | 2 | 0 | 14,498 | 31 |

Q3, Q4, Q7, Q8, Q9 and Q17 have no positives on an inactive code, and Q1 and Q2
use no terminology. In total, 23,711 positives (summed across questions, so a
row can count more than once) carry a code that is inactive in 20260731.

**HISTORY-MIN is close to useless here.** `SAME AS` alone recovers 4 of Q12's
194 concepts, 1 of Q14's 41 and 0 of Q6's 16. Almost all the recovery comes
from the additional associations in MOD (`REPLACED BY`, `WAS A`,
`PARTIALLY EQUIVALENT TO`). MAX adds a further 10 to 12 concepts in Q12, Q14
and Q15 on top of MOD. Anyone reaching for a history supplement on precision
grounds should know that MIN buys precision at the cost of nearly all the
recall.

**The 78 unrecoverable concepts cluster:**

- Retired obstetric findings (Q12/Q15): `Molar pregnancy`, `Short cord`,
  `Condition of amniotic membranes`, the `previous induced terminations of
  pregnancy` series, `O/E - vaginal examination` findings. 70 concepts are in
  scope for Q12 and 65 for Q15.
- Retired doxycycline products (Q12), including
  `Doxycycline monohydrate 100 mg oral capsule`.
- Four degenerative joint concepts (Q5/Q13): `Gouty arthropathy`,
  `Otto's pelvis`, `Degenerative lesion of articular cartilage of knee`,
  `Degeneration of cervicothoracic intervertebral disc`.
- One concept in Q14.

## Finding 2: what the latest edition does to the answers

Recomputing every flag against 20260731, versus the encounter-relative answers:

| Q | current | latest | +HIST-MOD | +HIST-MAX | gained | lost | net |
|---|---|---|---|---|---|---|---|
| Q4 hyperthyroidism | 10,859 | 10,629 | 10,629 | 10,629 | 0 | 230 | -230 |
| Q5 osteoarthritis in 2024 | 3,819 | 489 | 670 | 748 | 78 | **3,149** | -3,071 |
| Q10 bilateral condition | 7,038 | 2,802 | 6,754 | 7,045 | 7 | 0 | +7 |
| Q12 pregnant on teratogen | 347 | 316 | 853 | 856 | **515** | 6 | +509 |
| Q13 OA/RA, NSAID, low eGFR | 1,819 | 538 | 665 | 831 | 10 | **998** | -988 |
| Q14 open wound, upper limb | 22,600 | 10,582 | 20,764 | 22,631 | 583 | 552 | +31 |
| Q15 pregnant, high glucose | 461 | 341 | 772 | 820 | **463** | 104 | +359 |
| Q16 non-Strep joint infection | 1,472 | 1,089 | 1,089 | 1,469 | 11 | 14 | -3 |
| Q18 mineral supplement | 14,498 | 14,469 | 14,498 | 14,498 | 0 | 0 | +0 |

The table shows the gained, lost and net columns for +HIST-MAX. Questions not
listed do not move.

Two effects are mixed together in those losses, and they need separating.

**Retirement.** The code is inactive in the reference edition. A history
supplement can recover it only if SNOMED International recorded a historical
association. Q10 and Q14 show the best case: the naive latest-edition answer
loses 4,236 and 12,018 rows, and HISTORY-MAX recovers nearly all of them.

**Reclassification.** The concept is still active but is no longer inside the
ECL's subtree. There is nothing for a historical association to point at,
because nothing was made historical.

Splitting the lost rows by whether the recorded code is still active in 20260731:

| Q | rows lost under +HIST-MAX | code retired, no association | code still active (reclassified) |
|---|---|---|---|
| Q4 hyperthyroidism | 230 | 0 | **230** |
| Q5 osteoarthritis in 2024 | 3,149 | **2,566** | 583 |
| Q13 OA/RA, NSAID, low eGFR | 998 | **828** | 170 |

**This reverses a conclusion from the first run.** There, Q5 lost 952 rows with
only 8 in-scope retired concepts, so reclassification dominated. The first run
was unseeded. In the competition data the boost list over-samples exactly the
unrecoverable osteoarthritis concepts, so retired-with-no-association now
accounts for about 80% of Q5's loss. Reclassification remains, and it is the
whole story for Q4: 230 rows lost with no retired concept involved.

The osteoarthritis hierarchy itself did move. In the first run, `<<396275006
|Osteoarthritis|` held 431 concepts in 20250131 and 181 in 20260131. About 250
concepts left the subtree in one release, and only 8 of them were retired. The
others are still active; they are simply no longer classified as osteoarthritis.

What this means for analytics:

- "Use the latest edition, it is strictly better" is not a safe assumption. It is
  a different answer, not a corrected one.
- History supplements address *only* inactivation, and only when SNOMED
  International recorded an association. They give no protection against
  reclassification, and none against concepts retired without one.
- The mix of the two depends on the data. Whichever dominates, a latest-edition
  query cannot reproduce the encounter-relative answers.
- A cohort definition of the form `<<X` inherits every editorial decision about
  what belongs under X. Q5 and Q13 both depend on `osteoarthritis`, so a single
  restructure moved two independent questions.
- The latest edition can also pull rows in. Q12 and Q15 gain 515 and 463 rows
  because the pregnancy hierarchy is larger in newer editions. For example,
  *Pregnancy-induced hypertension* is a descendant only from the 2024 edition.
- Net movement can hide churn. Q14 nets to +31 but gains 583 and loses 552.
- Neither edition choice is "correct". Encounter-relative answers are not
  reproducible from the current release; latest-edition answers do not describe
  the clinical reality that was recorded. The choice has to be stated, not
  assumed.

## Finding 3: a methodological trap worth repeating publicly

Our first run reported Q18 losing 11,227 rows -- 55% of its positives -- while
having exactly **1** in-scope inactive concept. That mismatch was the tell.

`product_ecl_template_for_edition` switches product models mid-dataset: the
SNOMED CT international product hierarchy for pre-2025 encounters, AMT TPUU from
2025. Recomputing everything against the reference edition selected the AMT
template for every row, including pre-2025 rows whose recorded codes are
international clinical drugs. AMT TPUU structurally cannot contain those codes:

```
mineral / product    / 20240131:  237 concepts
mineral / amt-tpuu   / 20240131:    0 concepts   <-- wrong model for the data
```

Every one of the 11,018 lost rows had a 2021-2024 encounter; none were 2025+.
Expanding under both product models lost zero. Q18 was the question that exposed
it only because `mineral` is the one medicine criterion with no display-text
fallback to mask the failure.

The same artefact inflated the "unrecoverable" count from 48 to 94 in that run,
and made `374442007 |Methotrexate 5 mg oral tablet|` -- retired 20210930 -- look
like it had no historical association. It does; HISTORY-MOD recovers it.

The generalisable lesson: **when a measurement of terminology change spans a
model or extension boundary, the measurement apparatus has to span it too.**
Otherwise the tooling's own assumptions get reported as findings about the
terminology. The corrected reports expand the reference edition under both
product models (`REFERENCE_PRODUCT_TEMPLATES` in `analyse.py`). With the fix,
Q18 loses 29 rows under the naive latest-edition reading, and HISTORY-MOD
recovers all of them.

## Caveat on the medicine questions

The medicine criteria carry a display-text regex fallback, so a row can still
match on product name after its code drops out of the ECL. Q6 has 16 in-scope
inactive concepts across 2,214 positive rows yet shows zero movement under every
profile -- the regex absorbs it entirely. Q11 behaves the same way (4 concepts,
526 rows). The medicine questions therefore *understate* terminology
sensitivity.

The condition questions (Q3, Q4, Q5, Q8, Q10, Q14, Q16) have no fallback and show
the true exposure. Q18 is the exception among the medicines: its `mineral`
criterion has no fallback, which is why it moves at all.

Read the other way: a text fallback is a surprisingly effective mitigation
against both failure modes, at the cost of everything ECL gives you.

## Method

- Concept activity: FHIR `ValueSet/$expand` with an explicit `compose.include.
  concept` list and `activeOnly=false`. An ECL cannot answer this -- inactive
  concepts carry no relationships, so `<<X` never reaches them and any ECL
  expansion looks fully active regardless of `activeOnly`.
- Question scope: each question function is run against a recording view of the
  code sets, so the question-to-criteria mapping is observed rather than
  hand-maintained and cannot drift from the implementation.
- Recoverability: each criterion ECL re-expanded against the reference edition
  wrapped as `(<constraint>) {{ + HISTORY-<profile> }}`. Verified to work on
  `MINUS` compounds, on constraints already carrying a `{{ term = ... }}` filter,
  and on the AMT refset templates.
- `check_history_sets` asserts every supplemented expansion is a superset of its
  unsupplemented counterpart, since `expand_ecl` returns partial results on a
  request failure rather than raising -- which would otherwise surface as a
  confident "0 recovered".
- Retirement versus reclassification (Finding 2): for the positive rows of Q4,
  Q5 and Q13, the recorded `Clinical_Note_Code` is checked against the
  HISTORY-MAX expansion of the question's condition ECL in 20260731. A row that
  falls out of the expansion counts as retired if its code is inactive in 20260731
  and as reclassified if it is still active. This check is not part of
  `analyse.py` and its figures are not in `metrics.txt`. The totals match the
  lost columns in the table (3,149 for Q5, 998 for Q13, 230 for Q4). It treats
  the condition code as the only cause, which holds because the medicine criteria
  keep a display-text fallback.

## Status

These reports measure the alternative; they do not apply it. `solution.csv` is
computed against the encounter-relative editions and is not changed by any of the
analysis described here.
