# Terminology drift and its impact on analytics

Findings from measuring how SNOMED CT-AU edition changes affect the Data Golf
answer set. Measured 2026-08-06 against a 256,515-row dataset spanning six
editions (20210131 - 20260131), reference edition 20260131.

Reproduce with `python data-golf/analyse.py`; the numbers land in the
`INACTIVE CONCEPTS IN QUESTION SCOPE` and `EFFECT OF RECOMPUTING AGAINST ...`
sections of `metrics.txt`.

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

## Finding 1: retirement is the smaller problem

Of 21,435 distinct concepts in the dataset, 593 (2.8%) are inactive in the
20260131 edition. Only **171 fall inside a question's ECLs** -- the rest are
drift in codes no criterion refers to, and are harmless.

Those 171 touch **741 positive rows** in total, roughly 0.3% of the dataset.

History supplements recover most, but not all, and the profile matters far more
than expected:

| Question | in scope, inactive | HISTORY-MIN | HISTORY-MOD | HISTORY-MAX | unrecoverable |
|---|---|---|---|---|---|
| Q12 pregnant on teratogen | 132 | 4 | 87 | 91 | 41 |
| Q15 pregnant, high glucose | 82 | 4 | 42 | 45 | 37 |
| Q13 OA/RA, NSAID, low eGFR | 34 | 15 | 25 | 27 | 7 |
| Q6 ACE inhibitor | 16 | 0 | 15 | 16 | 0 |
| Q5 osteoarthritis in 2024 | 8 | 3 | 4 | 4 | 4 |
| Q11 F 15-49 on methotrexate | 4 | 0 | 4 | 4 | 0 |

**HISTORY-MIN is close to useless here.** `SAME AS` alone recovers 4 of Q12's
132 and 0 of Q6's 16. Almost all the recovery comes from the additional
associations in MOD (`REPLACED BY`, `WAS A`, `PARTIALLY EQUIVALENT TO`), and MAX
adds very little on top of MOD. Anyone reaching for a history supplement on
precision grounds should know that MIN buys precision at the cost of nearly all
the recall.

**48 concepts have no historical association at all** and cannot be recovered by
any profile. They cluster:

- Retired obstetric findings (Q12/Q15): `Molar pregnancy`, `Short cord`,
  `Condition of amniotic membranes`, the `previous induced terminations of
  pregnancy` series, `O/E - vaginal examination` findings.
- Retired doxycycline products (Q12): `Doxycycline monohydrate 50 mg oral
  capsule` and three siblings.
- Four degenerative joint concepts (Q5/Q13): `Gouty arthropathy`,
  `Otto's pelvis`, `Degenerative lesion of articular cartilage of knee`,
  `Degeneration of cervicothoracic intervertebral disc`.

## Finding 2: hierarchy change dominates, and no supplement touches it

Recomputing every flag against 20260131 with HISTORY-MAX, versus the
encounter-relative answers:

| Question | current | +HIST-MAX | gained | lost | net |
|---|---|---|---|---|---|
| Q5 osteoarthritis in 2024 | 1760 | 809 | 1 | **952** | -951 |
| Q13 OA/RA, NSAID, low eGFR | 812 | 531 | 1 | 282 | -281 |
| Q15 pregnant, high glucose | 793 | 1375 | **597** | 15 | +582 |
| Q12 pregnant on teratogen | 729 | 1289 | **560** | 0 | +560 |
| Q16 bacterial joint infection | 1552 | 1528 | 17 | 41 | -24 |
| Q10 bilateral condition | 2908 | 2914 | 6 | 0 | +6 |
| Q4 hyperthyroidism | 476 | 470 | 1 | 7 | -6 |

Set that against Finding 1: concept retirement touched **741 rows across all 18
questions**. Hierarchy change moved **952 rows in Q5 alone**, and Q5 has only 8
in-scope inactive concepts. The two failure modes are independent, they differ by
an order of magnitude, and **only the smaller one is addressable by history
supplements**.

The driver is visible directly in the hierarchy:

```
<<396275006 |Osteoarthritis|    20250131:  431 concepts
                                20260131:  181 concepts
```

250 concepts left the |Osteoarthritis| subtree in a single release. Only 8 were
retired. **The other ~242 are still active -- they are simply no longer
classified as osteoarthritis.** There is nothing for a historical association to
point at, because nothing was made historical. The concepts are fine; their
place in the hierarchy changed.

This is the finding that matters for analytics. It means:

- "Use the latest edition, it is strictly better" is not a safe assumption. It is
  a different answer, not a corrected one, and the delta is not bounded by the
  retirement rate.
- History supplements address *only* inactivation. They give no protection at all
  against reclassification, which here was the larger effect by a wide margin.
- A cohort definition of the form `<<X` inherits every editorial decision about
  what belongs under X. Q5 and Q13 both depend on `osteoarthritis`, so a single
  restructure moved two independent questions.
- Neither edition choice is "correct". Encounter-relative answers are not
  reproducible from the current release; latest-edition answers do not describe
  the clinical reality that was recorded. The choice has to be stated, not
  assumed.

## Finding 3: a methodological trap worth repeating publicly

Our first run reported Q18 losing 11,227 rows -- 55% of its positives -- while
having exactly **1** in-scope inactive concept. That mismatch was the tell.

`product_ecl_template_for_edition` switches product models mid-dataset: the
SNOMED CT international product hierarchy for pre-2025 encounters, AMT TPUU from
2025. Recomputing everything against 20260131 selected the AMT template for every
row, including pre-2025 rows whose recorded codes are international clinical
drugs. AMT TPUU structurally cannot contain those codes:

```
mineral / product    / 20240131:  237 concepts
mineral / amt-tpuu   / 20240131:    0 concepts   <-- wrong model for the data
```

Every one of the 11,018 lost rows had a 2021-2024 encounter; none were 2025+.
Expanding under both product models lost zero. Q18 was the question that exposed
it only because `mineral` is the one medicine criterion with no display-text
fallback to mask the failure.

The same artefact inflated the "unrecoverable" count from 48 to 94, and made
`374442007 |Methotrexate 5 mg oral tablet|` -- retired 20210930 -- look like it
had no historical association. It does; HISTORY-MOD recovers it.

The generalisable lesson: **when a measurement of terminology change spans a
model or extension boundary, the measurement apparatus has to span it too.**
Otherwise the tooling's own assumptions get reported as findings about the
terminology. The corrected reports expand the reference edition under both
product models (`REFERENCE_PRODUCT_TEMPLATES` in `analyse.py`).

## Caveat on the medicine questions

The medicine criteria carry a display-text regex fallback, so a row can still
match on product name after its code drops out of the ECL. Q6 has 16 in-scope
inactive concepts across 424 rows yet shows zero net movement -- the regex
absorbs it entirely. The medicine questions therefore *understate* terminology
sensitivity. The condition questions (Q3, Q4, Q5, Q8, Q10, Q16) have no fallback
and show the true exposure.

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
- Recoverability: each criterion ECL re-expanded against 20260131 wrapped as
  `(<constraint>) {{ + HISTORY-<profile> }}`. Verified to work on `MINUS`
  compounds, on constraints already carrying a `{{ term = ... }}` filter, and on
  the AMT refset templates.
- `check_history_sets` asserts every supplemented expansion is a superset of its
  unsupplemented counterpart, since `expand_ecl` returns partial results on a
  request failure rather than raising -- which would otherwise surface as a
  confident "0 recovered".

## Status

These reports measure the alternative; they do not apply it. `solution.csv` is
computed against the encounter-relative editions and is byte-identical before and
after this analysis was added.
