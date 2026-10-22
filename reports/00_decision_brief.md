# Decision brief: turn turnover counts into a review priority

AI-assisted synthesis of the existing study, October 22, 2026. The proposed review and intervention have not been carried out.

**Decision:** prioritize the first defensive actions after steal-linked losses in the ball-security review. Do not turn the estimated scoring gap directly into a promised coaching benefit.

![Adjusted 12-second scoring gaps across three overlapping samples](../figures/turnover_adjusted.png)

**Evidence:** the main within-game comparison is +0.69 opponent points over the next 12 game-clock seconds after steal-linked versus other turnovers, with a 95% interval of +0.58 to +0.79. It covers 1,007 turnovers in 79 games: 582 steal-linked and 425 others. Estimates remain positive under the reported score/clock and timeout restrictions. The restricted samples overlap the main sample, so their agreement is a sensitivity check rather than independent replication.

**Proposed next step:** use the existing event queue to code the turnover mechanism, location, number of defenders behind the ball and first recovery assignment. Include comparable non-steal losses. Treat missing linkage and ambiguous event ordering explicitly. Counts by player need an opportunity denominator before becoming player rankings; touches and passing exposure are not interchangeable with minutes.

**What would change the recommendation:** widespread errors in steal linkage, a materially different result under alternate event-order rules, or evidence that the selected review queue misses damaging non-steal live-ball losses. Outcomes at 8, 12 and 16 seconds are related measurements, not separate independent experiments.

**A prospective evaluation:** define one coaching cue and a fixed evaluation period before implementation. Track a process measure such as recovery-assignment execution alongside points allowed, annotate personnel and opponent changes, and compare with a predeclared baseline. Without a credible comparison, describe the results as a monitored pilot rather than a causal intervention estimate.

Sources: [full study](01_turnover_cost.md), [adjusted results](../results/turnover_adjusted.csv), [review queue](../results/turnover_review_queue.csv), and [execution limits](../VALIDATION_CURRENT.md).
