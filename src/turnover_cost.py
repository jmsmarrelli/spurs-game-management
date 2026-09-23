import json
import pandas as pd
from .common import ROOT, save_json
from .statistics import mean_ci, fixed_effect


def run():
    d = pd.read_csv(ROOT / "data/turnovers.csv.gz")
    d["live"] = d.kind.eq("Steal-linked").astype(int)
    d["player"] = d.player.fillna("Team turnover")
    rows = []
    for kind, g in d.groupby("kind"):
        for horizon in [8, 12, 16]:
            value, lo, hi = mean_ci(g, f"allowed_{horizon}")
            rows.append(
                dict(
                    kind=kind,
                    seconds=horizon,
                    events=len(g),
                    games=g.game_id.nunique(),
                    allowed=value,
                    lower=lo,
                    upper=hi,
                    any_score=g[f"allowed_{horizon}"].gt(0).mean(),
                )
            )
    pd.DataFrame(rows).to_csv(ROOT / "results/turnover_windows.csv", index=False)
    estimates = []
    for horizon in [8, 12, 16]:
        estimates.append(
            dict(
                sample="All eligible",
                seconds=horizon,
                **fixed_effect(d, f"allowed_{horizon}"),
            )
        )
    subset = d[d.margin.abs().le(15) & ~(d.period.ge(4) & d.seconds.le(120))]
    estimates.append(
        dict(
            sample="Competitive score and clock",
            seconds=12,
            **fixed_effect(subset, "allowed_12"),
        )
    )
    subset = d[d.timeout_12.eq(0)]
    estimates.append(
        dict(
            sample="No timeout in next 12 seconds",
            seconds=12,
            **fixed_effect(subset, "allowed_12"),
        )
    )
    pd.DataFrame(estimates).to_csv(ROOT / "results/turnover_adjusted.csv", index=False)
    players = (
        d.groupby("player")
        .agg(
            turnovers=("live", "size"),
            steal_linked=("live", "sum"),
            points_allowed_12=("allowed_12", "sum"),
        )
        .reset_index()
        .sort_values("steal_linked", ascending=False)
    )
    players.to_csv(ROOT / "results/turnover_players.csv", index=False)
    queue = (
        d[d.live.eq(1)]
        .sort_values(
            ["allowed_12", "game_id", "event_id"], ascending=[False, True, True]
        )
        .head(15)
    )
    queue.to_csv(ROOT / "results/turnover_review_queue.csv", index=False)
    summary = {
        "eligible_turnovers": len(d),
        "steal_linked": int(d.live.sum()),
        "primary": estimates[1],
        "groups": pd.DataFrame(rows).query("seconds==12").to_dict("records"),
    }
    save_json("turnover_summary.json", summary)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
