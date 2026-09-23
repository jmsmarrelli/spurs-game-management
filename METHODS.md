# Methods and data definitions

## Source audit

Two files are pinned in `data/source_manifest.json`: `nbastatsv3_2025` and `shotdetail_2025`. The suffix identifies the starting year, so both cover 2025–26. Downloads are SHA-256 verified. Source CSVs are kept in `data/raw` locally and excluded from publication archives.

Event order is `actionId` within a game. `actionNumber` joins to shot-chart `GAME_EVENT_ID`. `teamId` normally identifies an event’s club, but team events can instead store a team ID in `personId`. If `teamId` is zero and `personId` matches a recognized club ID, the latter is used. This retains team shot-clock turnovers and prevents a team event from being assigned to a player.

Home and away identities and dates come from shot records. Scores are carried forward within a game. Every retained game must satisfy unique ordered event IDs, complete period clocks, no clock reversal, nondecreasing scores, no single-row score jump above four points, and agreement between play-by-play and shot-chart shooter, value and result. Made field goals plus made free throws must reproduce both final scores.

The audit retains 79 of 82 games. Game 22500788 has a shot-feed disagreement. Games 22501041 and 22501146 contain score decreases; the latter also has an unexplained jump. Full games are excluded, rather than repairing individual events from guesses. This is an internal cross-source audit; official box-score certification has not been performed.

## Score windows

Clock strings preserve fractional seconds. A forward window starts after the anchor event and ends after the last event at or before the chosen elapsed game-clock horizon. Later events at the anchor clock are included, unless the anchor was deliberately placed at the end of that same-clock cluster. Events at the exact end boundary are included. Points are changes in carried-forward scores and therefore include free throws.

The turnover anchor is the turnover row. The timeout anchor is the final event at the made-basket clock, so same-clock points are assigned to the pre-timeout state. A prior window includes the anchor and events exactly at its earlier boundary. Windows remain inside one period. They measure game-clock time, not wall-clock time or a fixed number of possessions.

## Turnover exposure

Every retained Spurs turnover with at least 16 seconds left is eligible. An opposing steal description at the same clock and within the following three rows supplies the steal link. More than one candidate steal is rejected; delivered linked steal IDs are unique. There are 1,007 turnovers: 582 linked to a steal and 425 without one. The no-link category is not asserted to be a perfectly observed dead-ball category.

Raw outcomes are opponent scoreboard points inside 8, 12 and 16 seconds, plus the share of windows with positive scoring. All horizons use the same eligible sample. The primary model uses the 12-second outcome and a binary steal-link indicator. It adjusts for game fixed effects, score margin clipped to ±25 and divided by 25, squared scaled margin, period indicators and remaining period time divided by 720. Within-game centering removes game intercepts; a pseudoinverse solves least squares. Only games with both exposure categories enter the adjusted comparison; all 79 do so in this run.

The coefficient describes an adjusted association. It does not estimate the causal effect of replacing one pass with another or the full offensive and defensive cost of a turnover. Player usage, floor balance, locations and lineups are not controlled. Overlapping windows mean summed points are not a unique partition of the season’s conceded points.

Sensitivity checks restrict score margin to ±15 and exclude the final two minutes of Q4/OT, or remove windows with a subsequent timeout. The latter conditions on a post-turnover event and is descriptive, not a causal adjustment. Player counts include a separate team-turnover row. They have no touch or possession denominator. The 15-event review queue selects the largest observed 12-second scoring outcomes; it is not representative video coding.

## Timeout matching

Candidate anchors are opponent-made field goals in regulation quarters, with 60–660 seconds left. There must be exactly one opposing made field goal at that clock. A treated anchor has a Spurs timeout at the same clock. A comparison has no timeout by either team at that clock. Opponent-only and mixed-club timeout clusters are excluded. The source label does not reliably distinguish all mandatory, strategic or administrative reasons.

For each treated anchor, controls must share game and quarter, have a 90–240-second absolute clock separation, margin within six points and exactly equal prior-minute net scoring. Candidates are ranked by:

`distance = (clock difference / 120)^2 + (margin difference / 5)^2 + (prior net difference / 4)^2`

At most three are retained, with replacement across treated anchors. Each treated anchor has equal total weight; its controls split that weight evenly. The matched estimate is the mean of treated following-minute net points minus its weighted control mean. Exact prior-score matching makes the before/after difference-in-differences arithmetic equal to this post-window difference, but it does not establish the parallel-trends or exchangeability assumptions of a causal design.

There are 144 eligible timeout anchors; 43 match across 33 games, using 57 unique control anchors. Only matched states contribute to the primary estimate. Sensitivities allow a one- or two-point prior-score difference and keep all other rules. Matching uses observed preconditions; following-window outcomes are not used to select controls.

Balance reports mean differences divided by the standard deviation across the full candidate pool. It is a descriptive standardized difference, not a significance test. Lineups, fatigue, timeout inventory, exact prior score sequence and coach intent remain unmeasured. A comparison later in a game may also reflect effects of an earlier timeout beyond this study’s short window.

Later timeouts are permitted in both groups. The weighted rates are 26.4% for controls and 7.0% for treated anchors. The estimand is an observed comparison of an immediate timeout with no immediate timeout under subsequent real decisions, not an enforced timeout-free control period. Removing controls based on future timeouts would change the selection problem.

## Quarter-ending attempts

In Q1–Q3, select the first Spurs field goal attempt with 20–40 seconds left, at most once per game-quarter. No attempt in the window means no observation. The 143 selected quarters come from 74 games. The clock bands are [20,28), [28,34) and [34,40].

A return attempt requires an intervening opposing field goal attempt, turnover or nontechnical free throw before another Spurs field goal attempt. Consecutive Spurs shots following an offensive rebound alone do not establish a return. The marker is observable event evidence, not a complete possession reconstruction. It can miss foul-only scoring opportunities, and rare retained-ball foul sequences can complicate the possession interpretation. The index attempt itself may follow an offensive rebound.

Index-shot production is made field-goal points only. Closing net scoring is the scoreboard change from immediately before the index event to period end, Spurs minus opponent, including free throws. The earlier bands have more remaining time by construction; differences in closing points should not be interpreted as efficiency rates.

A logistic model predicts the return marker from `(seconds - 30) / 5`, margin clipped to ±20 and divided by 10, and Q2/Q3 indicators. Scikit-learn logistic regression uses L2 regularization with C=1 and an intercept. No hyperparameter search or post-January fitting is used. The first attempt’s outcome is excluded from predictors. Train dates are strictly before 2026-01-01 (59 quarters); test dates are January onward (84).

The comparator is the early return rate, held constant for every later observation. Log loss and Brier score are calculated on those later outcomes. Paired loss differences receive game-bootstrap intervals. Saved coefficients and predictions allow the model to be recalculated without an opaque model binary. The plotted curve holds the margin at zero and quarter at two; later clock-band points do not impose those same conditions and are not a formal calibration curve.

Selection on an observed attempt prevents policy evaluation at the beginning of a possession. The study does not observe the actual shot clock, the available alternative shot, the play call or intent to pursue a two-for-one. It estimates neither an optimal deadline nor a causal gain from shooting earlier.

## Uncertainty and reproducibility

All main intervals use 2,000 bootstrap resamples of games, seed 20260908, with 2.5th/97.5th percentiles. Regression refits use game sufficient statistics. Means weight events equally within the estimand, so games with more eligible events contribute more. Matching occurs entirely within each game; resampling games preserves shared controls and overlapping windows. Each matched timeout, rather than each control edge, is one analysis row.

The intervals are marginal, not adjusted for multiple testing. Prediction-loss intervals condition on the fitted early model and do not include training-sample uncertainty. Small subgroup samples and unobserved conditions remain limitations even when a bootstrap interval is narrow. The work is retrospective and exploratory; no preregistration is claimed.

## Derived tables

| File | Unit | Important fields |
| --- | --- | --- |
| `data/turnovers.csv.gz` | Eligible Spurs turnover | Game/event IDs, clock, subtype, steal link, 8/12/16-second score windows |
| `data/timeout_candidates.csv.gz` | Opponent-made-basket anchor | Treatment, preconditions, prior/following minute scores, later timeout flag |
| `data/quarter_attempts.csv.gz` | First qualifying shot in a quarter | Index clock, first shot points, intervening/return event IDs, closing score |
| `results/timeout_pairs.csv` | Treated-control edge | Same-game IDs, matching distance and control weight |
| `results/timeout_matched.csv` | Matched timeout | Treated and weighted control outcomes |
| `results/quarter_holdout.csv` | Later eligible quarter | Prediction, baseline, outcome and paired loss difference |
| `results/quarter_model.json` | Model specification | Intercept, coefficients, scaling and training cutoff |

SQL builds indexed cohort tables, clock-band summaries and ordered candidate counts. The test suite checks event logic, source-game membership, matching constraints, weight reconciliation and reproduction of later predictions from early data alone.
