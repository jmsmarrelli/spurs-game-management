import json
import sqlite3
import unittest

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from src.common import ROOT
from src.data import database
from src.events import SAS, normalize_team_ids, return_attempts, seconds, window
from src.quarter_clock import design
from src.statistics import fixed_effect, mean_ci, loss
from src.timeout_reset import match


class EventTests(unittest.TestCase):
    def test_clock_parser_preserves_fractional_seconds(self):
        self.assertEqual(seconds("PT01M23.50S"), 83.5)
        with self.assertRaises(ValueError):
            seconds("01:23")

    def test_team_turnover_identity_is_not_lost(self):
        d = pd.DataFrame({"teamId": [0, SAS, 0], "personId": [SAS, 1641705, 0]})
        np.testing.assert_array_equal(normalize_team_ids(d), [SAS, SAS, 0])

    def test_forward_window_counts_same_clock_points_and_excludes_late_score(self):
        d = pd.DataFrame(
            {
                "seconds": [100, 100, 95, 88, 87],
                "sas_score": [10] * 5,
                "opp_score": [10, 11, 13, 14, 17],
            }
        )
        self.assertEqual(window(d, 0, 12), (0, 4))
        self.assertEqual(window(d, 0, 8), (0, 3))

    def test_previous_window_does_not_leak_future_points(self):
        d = pd.DataFrame(
            {
                "seconds": [200, 160, 140, 100, 99],
                "sas_score": [0, 2, 4, 7, 10],
                "opp_score": [0, 0, 2, 2, 2],
            }
        )
        self.assertEqual(window(d, 3, 60, before=True), (7, 2))

    def test_own_offensive_rebound_shot_is_not_a_return_trip(self):
        d = pd.DataFrame(
            {
                "teamId": [SAS, SAS, SAS],
                "isFieldGoal": [1, 0, 1],
                "actionType": ["Missed Shot", "Rebound", "Made Shot"],
                "description": ["MISS", "Rebound", "Shot"],
            }
        )
        opponent, returning = return_attempts(d, 0)
        self.assertEqual(len(returning), 0)

    def test_opponent_turnover_can_precede_a_return_attempt(self):
        d = pd.DataFrame(
            {
                "teamId": [SAS, 1610612742, SAS],
                "isFieldGoal": [1, 0, 1],
                "actionType": ["Made Shot", "Turnover", "Missed Shot"],
                "description": ["Shot", "Turnover", "MISS"],
            }
        )
        opponent, returning = return_attempts(d, 0)
        self.assertEqual(opponent.index[0], 1)
        self.assertEqual(returning.index[0], 2)

    def test_technical_free_throw_alone_is_not_opponent_possession_evidence(self):
        d = pd.DataFrame(
            {
                "teamId": [SAS, 1610612742, SAS],
                "isFieldGoal": [1, 0, 1],
                "actionType": ["Missed Shot", "Free Throw", "Made Shot"],
                "description": ["MISS", "Free Throw Technical", "Shot"],
            }
        )
        self.assertEqual(len(return_attempts(d, 0)[1]), 0)


class EstimatorTests(unittest.TestCase):
    def test_game_intercepts_remove_between_game_bias(self):
        rows = []
        for game in range(1, 8):
            for flag in [0] * game + [1] * (9 - game):
                rows.append(
                    dict(
                        game_id=game,
                        live=flag,
                        margin=0,
                        seconds=360,
                        period=1,
                        y=10 * game + 2 * flag,
                    )
                )
        result = fixed_effect(pd.DataFrame(rows), "y", reps=100)
        self.assertAlmostEqual(result["estimate"], 2)
        self.assertAlmostEqual(result["lower"], 2)

    def test_constant_cluster_mean_and_loss(self):
        d = pd.DataFrame({"game_id": [1, 1, 2], "y": [3, 3, 3]})
        np.testing.assert_allclose(mean_ci(d, "y", 100), [3, 3, 3])
        np.testing.assert_allclose(loss([0, 1], [0.5, 0.5]), [-np.log(0.5)] * 2)

    def test_matching_uses_preconditions_not_following_score(self):
        rows = []
        for event, treated, clock, pre in [
            (1, 1, 400, -2),
            (2, 0, 500, -2),
            (3, 0, 550, -1),
            (4, 0, 410, -2),
        ]:
            row = dict(
                game_id=1,
                event_id=event,
                period=2,
                seconds=clock,
                margin=0,
                treated=treated,
                pre_net=pre,
                post_net=event,
                post_allowed=0,
                post_scored=event,
                later_timeout=0,
            )
            rows.append(row)
        d = pd.DataFrame(rows)
        a, _ = match(d)
        self.assertEqual(a.control_id.tolist(), [2])
        d["post_net"] = -d.post_net * 10
        b, _ = match(d)
        self.assertEqual(a.control_id.tolist(), b.control_id.tolist())


class DeliveredDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = pd.read_csv(ROOT / "data/turnovers.csv.gz")
        cls.c = pd.read_csv(ROOT / "data/timeout_candidates.csv.gz")
        cls.q = pd.read_csv(ROOT / "data/quarter_attempts.csv.gz")

    def test_cohorts_use_only_audited_games_and_unique_keys(self):
        audit = pd.read_csv(ROOT / "results/game_audit.csv")
        valid = set(audit[audit.status.eq("valid")].game_id)
        for d in [self.t, self.c, self.q]:
            self.assertFalse(d.duplicated(["game_id", "event_id"]).any())
            self.assertTrue(set(d.game_id) <= valid)
        self.assertFalse(self.q.duplicated(["game_id", "period"]).any())

    def test_scoring_horizons_are_nested(self):
        self.assertTrue(self.t.allowed_8.ge(0).all())
        self.assertTrue(self.t.allowed_12.ge(self.t.allowed_8).all())
        self.assertTrue(self.t.allowed_16.ge(self.t.allowed_12).all())
        self.assertTrue(self.t.seconds.ge(16).all())
        linked = self.t[self.t.steal_event_id.gt(0)]
        self.assertTrue(linked.kind.eq("Steal-linked").all())
        self.assertFalse(linked.duplicated(["game_id", "steal_event_id"]).any())

    def test_player_totals_include_team_turnovers(self):
        p = pd.read_csv(ROOT / "results/turnover_players.csv")
        self.assertEqual(int(p.turnovers.sum()), len(self.t))
        self.assertEqual(
            int(p.steal_linked.sum()), int(self.t.kind.eq("Steal-linked").sum())
        )

    def test_timeout_matching_constraints_and_weight_totals(self):
        pairs = pd.read_csv(ROOT / "results/timeout_pairs.csv")
        source = self.c.set_index(["game_id", "event_id"])
        for _, p in pairs.iterrows():
            t = source.loc[(p.game_id, p.event_id)]
            c = source.loc[(p.game_id, p.control_id)]
            self.assertEqual(t.period, c.period)
            self.assertEqual(t.treated, 1)
            self.assertEqual(c.treated, 0)
            self.assertEqual(t.pre_net, c.pre_net)
            self.assertLessEqual(abs(t.margin - c.margin), 6)
            self.assertTrue(90 <= abs(t.seconds - c.seconds) <= 240)
        np.testing.assert_allclose(
            pairs.groupby(["game_id", "event_id"]).weight.sum(), 1
        )

    def test_timeout_effect_reconciles_to_weighted_pairs(self):
        pairs = pd.read_csv(ROOT / "results/timeout_pairs.csv")
        diff = (
            pairs.assign(
                difference=lambda d: d.weight
                * (d.treated_post_net - d.control_post_net)
            )
            .groupby(["game_id", "event_id"])
            .difference.sum()
            .mean()
        )
        summary = json.loads((ROOT / "results/timeout_summary.json").read_text())
        self.assertAlmostEqual(diff, summary["matched_difference"])

    def test_return_event_order_and_clock_limits(self):
        d = self.q
        self.assertTrue(d.period.between(1, 3).all())
        self.assertTrue(d.seconds.between(20, 40).all())
        yes = d[d.return_attempt.eq(1)]
        no = d[d.return_attempt.eq(0)]
        self.assertTrue(yes.first_opp_event.gt(0).all())
        self.assertTrue(yes.return_event.gt(0).all())
        self.assertTrue(yes.return_seconds.le(yes.seconds).all())
        self.assertTrue(no.return_event.eq(0).all())

    def test_later_forecasts_reproduce_from_early_only_fit(self):
        early = self.q[self.q.date < "2026-01-01"]
        later = self.q[self.q.date >= "2026-01-01"]
        model = LogisticRegression(C=1, max_iter=2000).fit(
            design(early), early.return_attempt
        )
        held = pd.read_csv(ROOT / "results/quarter_holdout.csv")
        self.assertEqual(later.event_id.tolist(), held.event_id.tolist())
        np.testing.assert_allclose(
            model.predict_proba(design(later))[:, 1], held.prediction, atol=1e-10
        )
        np.testing.assert_allclose(held.baseline, early.return_attempt.mean())
        self.assertTrue(held.date.ge("2026-01-01").all())

    def test_sql_reconciles_with_derived_records(self):
        database()
        with sqlite3.connect(ROOT / "data/research.sqlite") as con:
            self.assertEqual(
                con.execute("SELECT SUM(turnovers) FROM turnover_windows").fetchone()[
                    0
                ],
                len(self.t),
            )
            self.assertEqual(
                con.execute(
                    "SELECT SUM(quarters) FROM quarter_clock_groups"
                ).fetchone()[0],
                len(self.q),
            )
            self.assertEqual(
                con.execute(
                    "SELECT SUM(candidates) FROM timeout_game_counts"
                ).fetchone()[0],
                len(self.c),
            )


if __name__ == "__main__":
    unittest.main()
