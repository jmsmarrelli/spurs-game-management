import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from .common import ROOT, save_json
from .statistics import mean_ci, loss


def design(d):
    return np.column_stack(
        [
            (d.seconds - 30) / 5,
            d.margin.clip(-20, 20) / 10,
            d.period.eq(2),
            d.period.eq(3),
        ]
    )


def run():
    d = pd.read_csv(ROOT / "data/quarter_attempts.csv.gz")
    rows = []
    for band, g in d.groupby("clock_band"):
        p, lo, hi = mean_ci(g, "return_attempt")
        fg, flo, fhi = mean_ci(g, "first_points")
        g = g.copy()
        g["closing_net"] = g.close_scored - g.close_allowed
        net, nlo, nhi = mean_ci(g, "closing_net")
        rows.append(
            dict(
                clock_band=band,
                attempts=len(g),
                games=g.game_id.nunique(),
                return_rate=p,
                lower=lo,
                upper=hi,
                first_ppa=fg,
                first_low=flo,
                first_high=fhi,
                three_share=g.first_three.mean(),
                closing_net=net,
                net_lower=nlo,
                net_upper=nhi,
            )
        )
    pd.DataFrame(rows).to_csv(ROOT / "results/quarter_groups.csv", index=False)
    early = d[d.date < "2026-01-01"]
    later = d[d.date >= "2026-01-01"].copy()
    baseline = early.return_attempt.mean()
    model = LogisticRegression(C=1, max_iter=2000).fit(
        design(early), early.return_attempt
    )
    later["prediction"] = model.predict_proba(design(later))[:, 1]
    later["baseline"] = baseline
    later["loss_difference"] = loss(later.return_attempt, later.prediction) - loss(
        later.return_attempt, later.baseline
    )
    diff, lo, hi = mean_ci(later, "loss_difference")
    later.to_csv(ROOT / "results/quarter_holdout.csv", index=False)
    curve = pd.DataFrame({"seconds": np.linspace(20, 40, 81), "margin": 0, "period": 2})
    curve["return_probability"] = model.predict_proba(design(curve))[:, 1]
    curve.to_csv(ROOT / "results/quarter_prediction_curve.csv", index=False)
    coefs = dict(
        zip(
            ["clock_per_5_seconds", "margin_per_10_points", "period_2", "period_3"],
            model.coef_[0],
        )
    )
    model_card = {
        "intercept": float(model.intercept_[0]),
        "coefficients": coefs,
        "C": 1,
        "training_cutoff": "2026-01-01",
        "features": "Clock centered at 30 seconds / 5, margin clipped to ±20 / 10, Q2 and Q3 indicators",
        "training_events": len(early),
    }
    save_json("quarter_model.json", model_card)
    summary = {
        "eligible_quarters": len(d),
        "games": d.game_id.nunique(),
        "training_quarters": len(early),
        "test_quarters": len(later),
        "training_return_rate": baseline,
        "model_logloss": float(loss(later.return_attempt, later.prediction).mean()),
        "baseline_logloss": float(loss(later.return_attempt, later.baseline).mean()),
        "model_brier": float(((later.prediction - later.return_attempt) ** 2).mean()),
        "baseline_brier": float(((later.baseline - later.return_attempt) ** 2).mean()),
        "loss_difference": diff,
        "lower": lo,
        "upper": hi,
        "groups": rows,
    }
    save_json("quarter_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
