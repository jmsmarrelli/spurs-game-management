# Delivered run

The full pipeline completed from two checksum-verified public source archives. All three notebooks executed successfully with four populated code cells each and no error outputs. Eighteen automated tests passed locally.

The checks cover team-event identity, fractional clocks, score-window boundaries, same-clock free throws, return-attempt definitions, game-level estimation, matching rules, equal timeout weights, cohort membership, SQL totals and reproduction of later predictions using only early-season training data.

The source audit retained 79 of 82 games. Full exclusions are in `results/game_audit.csv`. Within retained games, scores reconcile to recorded made shots and free throws, clocks are ordered and shot records match the separate shot feed. These checks are internal consistency checks, not independent official certification.

Nine figures were inspected visually. Each HTML article contains three embedded images.

The statistical limits remain explicit in the articles: steal linkage is not a perfect live/dead-ball classification, strict timeout matching retains only 43 events, later timeouts remain possible in both groups, and the quarter-clock prediction test has only 84 later observations. None of the studies establishes a causal coaching policy.
