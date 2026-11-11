# Data Golf 2026: what 13 teams taught us: speaker notes

## Slide 1 (cover)

Data Golf was a free Kaggle competition: 18 yes/no clinical questions over a synthetic SNOMED CT-coded dataset. I want to use my ten minutes on what the submissions told us, because the patterns are ones every analyst working with coded data will meet.

## Slide 2 (round)

Six SNOMED CT-AU editions, and one rule: answer each encounter with the edition current on its date. Medicines switch from SNOMED CT clinical drugs to AMT products in 2025. We picked questions where the terminology moved between editions, and we over-sampled codes that were later retired, so drift would show. Those retirement rates are by design, not what you would see in real data. Scoring was macro F1: for each question, how well your Trues match the key, penalising both misses and false alarms, averaged over the 18 questions. The top three finished within a quarter of a percentage point. So the interesting question is where everyone else lost points.

## Slide 3 (points)

Each bar is the average F1 lost on a question. Most holes were par for everyone. The losses concentrate where teams disagreed: the two pregnancy questions, Q18 mineral supplements, Q16 joint infection and Q13 arthritis with NSAIDs. Q12, the hardest hole, needed a home-made teratogen list, because the SNOMED CT teratogen concept has no subtypes. But disagreement only shows you where teams differ. The biggest single lesson came from a question where nine teams agreed and were wrong together, and you only find that by asking whether the definition itself is right. That is where I will start.

## Slide 4 (course)

For reference only, no need to read these out. The five dark rows are where the teams disagreed most: the two pregnancy questions, mineral supplements, the bacterial joint infection and arthritis with an NSAID and low eGFR. The rest were largely par for the course.

## Slide 5 (par)

Before the event we gave every hole a par: how hard we expected it to play, from 1 to 6. Par was a good guide at the hard end. Q12, par 6, played hardest. It was weaker in the middle: Q15 was rated 4 and played second hardest, because identifying pregnancy dominated it, while Q10 and Q11, also rated 4, played among the easiest.

## Slide 6 (q4)

Q4 asked for hyperthyroidism according to the clinical note. 1,271 rows carry familial dysalbuminaemic hyperthyroxinaemia, FDH, or its transthyretin cousin. Both sit under Hyperthyroidism in the hierarchy, so a plain descendants query picks them up. But these patients are euthyroid: a variant binding protein raises measured total T4 while TSH is normal. The FDH literature warns specifically against treating them as hyperthyroid. Nine teams said True on every one of those rows, and seven produced an identical answer column, which suggests essentially the same query. Subsumption answers the question the hierarchy asks, which is not always the clinical question. [Optional: say what happens next for this part of the hierarchy, if it is going to editorial review.]

## Slide 7 (q15)

Pregnancy was the hardest part of the competition. Seven concepts are not pregnancy in the early editions and are in later ones; Iron deficiency anaemia of pregnancy is the clearest. On the chart, the answer key steps up at the 2025 edition, Teams 1 to 3 largely follow it, and the average of Teams 4 to 13 barely moves. The strongest evidence is in the errors: seven teams have most of their pregnancy false positives in the 2021 and 2022 editions, and 77 to 100 percent of those rows are notes that only count as pregnancy from 2023. A later grouping was applied to earlier encounters. That is reclassification, not retirement, so no history supplement would catch it. Confidence is medium: seven concepts, 7 to 22 rows per concept and year. Edition handling was a large part of the gap between the podium and the pack.

## Slide 8 (q18)

Mineral supplement was ambiguous by design; the wording follows ATC A12. The SNOMED CT Mineral supplement substance has subtypes, but no product uses them as an ingredient, so participants had to build their own list. The key follows the ingredient, and the question named no dose form, so a zinc oxide nappy-rash ointment counts. Read the question by clinical intent and you drop those. Start from the element and you miss compounds: Is modification of links ferrous fumarate and zinc sulfate to their element, but not ferrous sulfate or zinc oxide. Going through product ingredients is more reliable. Neither reading is wrong; the definition was the hard part, not the query.

## Slide 9 (q14)

Q14 was par 3 and mostly played that way, but look at where the errors fall. The answer key works from the modelled finding site: a finger metacarpal fracture is in the hand, so it stays in; digital vessel injuries stay in; traumatic amputations of fingers are out. You could argue a digital artery injury is a finger wound, and that is the point: the model makes a choice, and teams that filtered on the words finger or digital went wrong in both directions. No error was shared by more than three teams. Use the attributes, not the strings, and know what the model decided.

## Slide 10 (learnings)

Five things to take away. One: state your edition strategy; encounter-time and latest-edition give different answers. Two: history supplements are not a safety net. On Q5, querying the latest edition drops 3,819 positives to 748, even with the most generous supplement, because many concepts were retired without an association or simply moved. Three: expand your value set and read it against your data; that would have caught Q4. Four: use the model's attributes, not words in the term. Five: write the definition before the ECL, because that is where the real disagreement lives.

## Slide 11 (close)

Thanks to everyone who entered. Womp Ratter, Joss Markham and Dougal Fleming from Dedalus, take the win: first on the private leaderboard, which Kaggle uses for final standings, and first overall. Kenny-Bytes, Ken Lee from Makoha, led the public leaderboard by one ten-thousandth; a photo finish. Marcus Baw, of Everything Digital Health, was a clear third. If you take one thing away: state your edition strategy, and write the definition before the ECL. The full report is on the competition page.
