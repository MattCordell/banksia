# ECL expansion comparison across SNOMED CT-AU editions

Member counts for each criterion ECL, expanded against every edition in `PERIODS`. Rows whose spread reaches **20%** are flagged.

Spread is `(max - min) / max` over the editions that are directly comparable. Condition ECLs are scored across all six editions. Medicine ECLs are scored within each era separately, because `|Medicinal product|` (373873005) grows 6.6x at the 2025 edition -- 25,306 members to 166,511 -- as AMT trade products land in the hierarchy. That boundary step is shown as context, not a defect.

| `<<373873005` baseline | 20210131 | 20220131 | 20230131 | 20240131 | 20250131 | 20260131 |
|---|---|---|---|---|---|---|
| members | 22503 | 23215 | 24895 | 25306 | 166511 | 172840 |

**9 of 24 expansions flagged** for within-era spread at the 20% threshold.

**3 medicine expansion(s) shrink across the 2025 boundary** while the product hierarchy grows 6.6x - see Boundary anomalies below.

## Condition ECLs

| Criterion | 20210131 | 20220131 | 20230131 | 20240131 | 20250131 | 20260131 | Spread |  |
|---|---|---|---|---|---|---|---|---|
| `hyperthyroidism` | 67 | 21 | 21 | 22 | 23 | 26 | 69% | FLAG |
| `bilateral` | 1147 | 1422 | 1605 | 1687 | 2366 | 2833 | 60% | FLAG |
| `pregnancy` | 1602 | 1258 | 775 | 1314 | 1266 | 1232 | 52% | FLAG |
| `rheumatoid_arthritis` | 60 | 122 | 108 | 108 | 112 | 114 | 51% | FLAG |
| `osteoarthritis` | 294 | 311 | 319 | 311 | 350 | 181 | 48% | FLAG |
| `bacterial_joint_non_strep` | 69 | 74 | 80 | 87 | 92 | 106 | 35% | FLAG |
| `fungal_foot` | 9 | 10 | 10 | 10 | 10 | 11 | 18% |  |
| `healthy` | 21 | 22 | 22 | 22 | 22 | 22 | 5% |  |

## Medicine ECLs

| Criterion | 20210131 | 20220131 | 20230131 | 20240131 | 20250131 | 20260131 | Spread | 2025 step |  |
|---|---|---|---|---|---|---|---|---|---|
| `methotrexate` | 9 | 9 | 4 | 6 | 48 | 51 | 56% | +700% | FLAG |
| `valproate` | 23 | 24 | 28 | 31 | 35 | 41 | 26% | +13% | FLAG |
| `warfarin` | 4 | 4 | 4 | 4 | 12 | 15 | 20% | +200% | FLAG |
| `paracetamol` | 195 | 196 | 232 | 235 | 704 | 710 | 17% | +200% |  |
| `statin` | 91 | 91 | 106 | 109 | 786 | 810 | 17% | +621% |  |
| `nsaid_oral` | 380 | 383 | 436 | 454 | 1195 | 1217 | 16% | +163% |  |
| `arb` | 116 | 117 | 136 | 136 | 761 | 803 | 15% | +460% |  |
| `oral_iron` | 52 | 55 | 56 | 60 | 191 | 204 | 13% | +218% |  |
| `acei` | 140 | 150 | 157 | 158 | 706 | 719 | 11% | +347% |  |
| `tetracycline` | 18 | 18 | 16 | 16 | 1 | 1 | 11% | -94% | SHRINKS |
| `mineral` | 55 | 56 | 60 | 60 | 731 | 768 | 8% | +1118% |  |
| `loop_diuretic` | 56 | 56 | 61 | 61 | 63 | 68 | 8% | +3% |  |
| `isotretinoin` | 13 | 13 | 13 | 13 | 34 | 35 | 3% | +162% |  |
| `cardiac_glycoside` | 16 | 16 | 16 | 16 | 7 | 7 | 0% | -56% | SHRINKS |
| `digoxin` | 13 | 13 | 13 | 13 | 7 | 7 | 0% | -46% | SHRINKS |
| `carbimazole` | 4 | 4 | 4 | 4 | 5 | 5 | 0% | +25% |  |

## Flagged expansions

### `hyperthyroidism` (condition)

- Ingredient/condition ECL: `<<34486009`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **69%** (20210131=67, 20220131=21, 20230131=21, 20240131=22, 20250131=23, 20260131=26)
- Largest single step: 20210131 -> 20220131 -69%

### `bilateral` (condition)

- Ingredient/condition ECL: `<<404684003 {{ term = "bilateral" }}`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **60%** (20210131=1147, 20220131=1422, 20230131=1605, 20240131=1687, 20250131=2366, 20260131=2833)
- Largest single step: 20240131 -> 20250131 +40%

### `methotrexate` (medicine)

- Ingredient/condition ECL: `<<387381009`
- Product template: product -> amt-tpuu at 2025
- Spread 2021-2024: **56%** (20210131=9, 20220131=9, 20230131=4, 20240131=6)
- Spread 2025-2026: **6%** (20250131=48, 20260131=51)
- Template switch 20240131 -> 20250131: +700% (expected; different product model)
- Largest single step: 20240131 -> 20250131 +700%

### `pregnancy` (condition)

- Ingredient/condition ECL: `(<<118185001) MINUS ((<<118185001 {{term = "postpartum"}}) OR (<<118185001 {{term = "postnatal"}}) OR (<<118185001 {{term = "puerper"}}))`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **52%** (20210131=1602, 20220131=1258, 20230131=775, 20240131=1314, 20250131=1266, 20260131=1232)
- Largest single step: 20230131 -> 20240131 +70%

### `rheumatoid_arthritis` (condition)

- Ingredient/condition ECL: `<<69896004`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **51%** (20210131=60, 20220131=122, 20230131=108, 20240131=108, 20250131=112, 20260131=114)
- Largest single step: 20210131 -> 20220131 +103%

### `osteoarthritis` (condition)

- Ingredient/condition ECL: `(<<396275006) MINUS ((<<90560007) OR (<<239838005))`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **48%** (20210131=294, 20220131=311, 20230131=319, 20240131=311, 20250131=350, 20260131=181)
- Largest single step: 20250131 -> 20260131 -48%

### `bacterial_joint_non_strep` (condition)

- Ingredient/condition ECL: `(<<363162000:246075003=((<<409822003) MINUS (<<58800005)))`
- Product template: n/a (matched against Clinical_Note_Code)
- Spread all editions: **35%** (20210131=69, 20220131=74, 20230131=80, 20240131=87, 20250131=92, 20260131=106)
- Largest single step: 20250131 -> 20260131 +15%

### `valproate` (medicine)

- Ingredient/condition ECL: `<<264325000`
- Product template: product -> amt-tpuu at 2025
- Spread 2021-2024: **26%** (20210131=23, 20220131=24, 20230131=28, 20240131=31)
- Spread 2025-2026: **15%** (20250131=35, 20260131=41)
- Template switch 20240131 -> 20250131: +13% (expected; different product model)
- Largest single step: 20250131 -> 20260131 +17%

### `warfarin` (medicine)

- Ingredient/condition ECL: `<<372756006`
- Product template: product -> amt-tpuu at 2025
- Spread 2021-2024: **0%** (20210131=4, 20220131=4, 20230131=4, 20240131=4)
- Spread 2025-2026: **20%** (20250131=12, 20260131=15)
- Template switch 20240131 -> 20250131: +200% (expected; different product model)
- Largest single step: 20240131 -> 20250131 +200%

## Boundary anomalies

These medicine criteria have **fewer** matching products in the 2025 edition than in 2024, even though `|Medicinal product|` grew 6.6x. Sometimes that is real -- Australia may register fewer trade products for a substance than the international hierarchy lists -- but it is also the signature of an ECL that does not reach the AMT product model. Worth confirming against the actual products before publishing.

| Criterion | 2024 | 2025 | Step | Template |
|---|---|---|---|---|
| `tetracycline` | 16 | 1 | -94% | product -> amt-tpuu at 2025 |
| `cardiac_glycoside` | 16 | 7 | -56% | product -> amt-tpuu at 2025 |
| `digoxin` | 13 | 7 | -46% | product -> amt-tpuu at 2025 |

## ECL expressions

| Criterion | Group | ECL |
|---|---|---|
| `healthy` | condition | `(<<102499006) OR (<<160245001)` |
| `hyperthyroidism` | condition | `<<34486009` |
| `osteoarthritis` | condition | `(<<396275006) MINUS ((<<90560007) OR (<<239838005))` |
| `rheumatoid_arthritis` | condition | `<<69896004` |
| `fungal_foot` | condition | `(<<3218000) AND ((<404684003:363698007=(<<56459004)) OR (<<6020002))` |
| `bilateral` | condition | `<<404684003 {{ term = "bilateral" }}` |
| `pregnancy` | condition | `(<<118185001) MINUS ((<<118185001 {{term = "postpartum"}}) OR (<<118185001 {{term = "postnatal"}}) OR (<<118185001 {{term = "puerper"}}))` |
| `bacterial_joint_non_strep` | condition | `(<<363162000:246075003=((<<409822003) MINUS (<<58800005)))` |
| `acei` | medicine | `<<372733002` |
| `arb` | medicine | `<<372913009` |
| `cardiac_glycoside` | medicine | `<<406759007` |
| `digoxin` | medicine | `<<387461009` |
| `paracetamol` | medicine | `<<387517004` |
| `methotrexate` | medicine | `<<387381009` |
| `tetracycline` | medicine | `<<372809001` |
| `carbimazole` | medicine | `<<395831005` |
| `statin` | medicine | `<<372912004` |
| `warfarin` | medicine | `<<372756006` |
| `valproate` | medicine | `<<264325000` |
| `isotretinoin` | medicine | `<<387208003` |
| `nsaid_oral` | medicine | `<<372665008` |
| `loop_diuretic` | medicine | `<<372691009` |
| `oral_iron` | medicine | `<<767270007` |
| `mineral` | medicine | `<<87918000 MINUS (<<39972003 OR <<88480006 OR <<50213009)` |
