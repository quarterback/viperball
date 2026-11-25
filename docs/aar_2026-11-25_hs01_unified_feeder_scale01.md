# HS-01 — Unified high school competition and college recruiting

## Integration baseline and prior evidence

Branch engine/hs01-unified-college-feeder starts at GitHub's #376 merge result 9499cc8f515db56b245c1cf1e952707d979591b4, with main's SCALE-01 commit 8a06988ce2dfd9a858f75a0b077ddc08604f18ee included as an ancestor (compare reports ahead, zero behind). Includes the WEA-02 documentation, not a new weather implementation.

DEF-11 #373 completed both its integrated and CCH-03/04 workflows successfully (45513973929, 45513973974). #376 completed five regression workflows and its reduced integrated job (138876274197); both national jobs (138879619973, 138879620071) failed on the same duplicate opening player ID: Kimberley Campbell, Boston College and West Virginia. No national roster-continuity pass claimed. The new candidate namespaces fresh college roster IDs by entry year, program and slot; finalized saved roster IDs remain authoritative.

## Implemented

- The HS competition is the authoritative physical roster and development history. Assign stable player IDs by school, entry year and slot. Keep returning players' identities, school, class progression and attributes when the league advances. The previous season is not mutated.
- School keys distinguish schools with the same display name across states; schedules, bracket winners and team links use exact keys. Title-game player statistics attach to the player ID.
- The recruiting pipeline is a view of actual competition cohorts, not an independently generated league. Preserve the existing bounded class-size policy (at least 300, 12 per college program), carry tracked returning prospects forward, sample new prospects deterministically without selecting on true talent, and retain individual scouting/recruiting metadata. Use identical position-weighted true overall and physical attributes on HS, Recruit and college PlayerCard records. Existing recruit academic/personality generation is reused with identity-seeded RNG; no synthetic physical traits are retained.
- The actual tracked senior cohort becomes the next college signing pool. Untracked graduating seniors are a separate reserve for walk-ons, used before generating explicit emergency walk-ons. These do not enlarge the scholarship recruiting board. Signed reserve profiles persist with the latest signing pool.
- Interactive and automated dynasty recruiting share feeder lifecycle; stats-site scouting and HS pages read the same league. Persist competition, schedule, scores and pipeline in both file and DB saves; compress the larger DB league payload. HS simulation retains the established quick regular season and full-engine title games.
- Legacy saves without authoritative HS competition state initialize a new competition-backed prospect view; do not invent identity mappings between unrelated historic synthetic prospects. Already saved college identities are not rewritten. Season-only synthetic recruiting remains separate.

## Acceptance and limitations

Six focused tests exercise same-player rating parity, graduation, returning prospects, duplicate school names, roundtrip, fresh college identity collisions and real HS reserve walk-ons. Existing integrated workflow explicitly runs feeder, college cohort and SCALE-01 regressions, then three reduced three-season dynasties, rare tactics and two national two-season dynasties. The benchmark now checks exact senior pool and reserve membership, retirement of graduating HS players, retained tracked cohorts, college signing identity and physical attributes, competition save digest, pipeline save parity, and earlier staff/roster/schedule/score gates.

No new coaching adaptation, scoring or package utilization targets. The combined candidate must pass runtime validation before CCH-08. The latest signing pool is saved, not a separate exhaustive archive of every prior HS season. Emergency walk-ons remain possible if the real graduating reserve has no matching position. Standalone noninteractive college roster maintenance and midseason save/resume need separate broader validation; no live-site verification claimed.

Status: implementation committed, candidate CI pending.
