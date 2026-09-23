from pathlib import Path
import os, json

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Rectangle, Circle
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
from .common import ROOT
from .statistics import mean_ci

BLACK = "#15191D"
SILVER = "#79858C"
TEAL = "#147D92"
ORANGE = "#BB4A26"
LIGHT = "#DCE3E6"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": BLACK,
        "axes.labelcolor": BLACK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": LIGHT,
        "xtick.color": SILVER,
        "ytick.color": BLACK,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "svg.fonttype": "none",
    }
)


def save(fig, name, caption):
    fig.text(0.045, 0.025, caption, fontsize=9, color=SILVER)
    fig.savefig(
        ROOT / f"figures/{name}.png",
        dpi=180,
        bbox_inches="tight",
        metadata={"Software": None},
    )
    fig.savefig(
        ROOT / f"figures/{name}.svg",
        bbox_inches="tight",
        metadata={"Creator": None, "Date": None, "Description": caption},
    )
    plt.close(fig)


def run():
    d = pd.read_csv(ROOT / "results/turnover_windows.csv")
    fig, ax = plt.subplots(figsize=(9.7, 5.2))
    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.26, top=0.82)
    for kind, color in [("Steal-linked", ORANGE), ("No linked steal", SILVER)]:
        g = d[d.kind.eq(kind)].sort_values("seconds")
        ax.plot(
            g.seconds,
            g.allowed,
            "o-",
            color=color,
            label=f"{kind} ({int(g.events.iloc[0])} turnovers)",
            lw=2,
            ms=7,
        )
        ax.fill_between(g.seconds, g.lower, g.upper, color=color, alpha=0.12)
    ax.set_xticks([8, 12, 16])
    ax.set_ylim(0, 1.6)
    ax.set_xlabel("Game-clock seconds after the turnover")
    ax.set_ylabel("Opponent points per turnover")
    ax.set_title(
        "Opponent scoring arrives sooner after recorded steals", loc="left", pad=18
    )
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    save(
        fig,
        "turnover_clock",
        "Same turnover sample at all horizons. Shading: 95% game-bootstrap intervals; includes free throws.",
    )
    d = pd.read_csv(ROOT / "results/turnover_adjusted.csv").query("seconds==12")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(left=0.36, right=0.96, bottom=0.24, top=0.82)
    labels = ["All eligible", "Competitive score / clock", "No timeout in the next 12s"]
    for i, (_, v) in enumerate(d.iterrows()):
        ax.errorbar(
            v.estimate,
            i,
            xerr=[[v.estimate - v.lower], [v.upper - v.estimate]],
            fmt="o",
            capsize=4,
            color=ORANGE,
            ms=7,
        )
        ax.text(
            v.estimate,
            i + 0.20,
            f"{v.estimate:+.2f} points · {int(v.events)} turnovers",
            ha="center",
            va="top",
            fontsize=9,
        )
    ax.set_yticks(range(3), labels)
    ax.set_ylim(2.5, -0.5)
    ax.set_xlim(-0.05, 1)
    ax.axvline(0, color=LIGHT)
    ax.set_xlabel("Adjusted difference in opponent points over 12 seconds")
    ax.set_title("The short-window gap survives context checks", loc="left", pad=18)
    save(
        fig,
        "turnover_adjusted",
        "Steal-linked minus no linked steal. Game fixed effects with score, clock and period controls; 95% intervals.",
    )
    d = pd.read_csv(ROOT / "results/turnover_players.csv").head(8)
    fig, ax = plt.subplots(figsize=(9.7, 5.4))
    fig.subplots_adjust(left=0.19, right=0.93, bottom=0.22, top=0.81)
    ax.barh(d.player, d.steal_linked, color=ORANGE, height=0.65)
    for i, (_, v) in enumerate(d.iterrows()):
        ax.text(
            v.steal_linked + 2,
            i,
            f"{int(v.steal_linked)} of {int(v.turnovers)}",
            va="center",
            fontsize=10,
        )
    ax.invert_yaxis()
    ax.set_xlim(0, d.steal_linked.max() * 1.4)
    ax.set_xlabel("Turnovers linked to a recorded steal")
    ax.set_title(
        "A starting list for reviewing ball-security possessions", loc="left", pad=18
    )
    save(
        fig,
        "turnover_players",
        "Counts in the retained sample. Workload and touches differ; this is not a player turnover-rate ranking.",
    )
    d = pd.read_csv(ROOT / "results/timeout_trajectories.csv")
    meta = json.loads((ROOT / "results/timeout_summary.json").read_text())
    fig, ax = plt.subplots(figsize=(9.5, 5.1))
    fig.subplots_adjust(left=0.13, right=0.96, bottom=0.25, top=0.82)
    for group, color, label in [
        ("treated", BLACK, "Spurs timeout"),
        ("control", TEAL, "Matched comparison"),
    ]:
        g = d[d.group.eq(group)].set_index("phase").loc[["pre", "post"]]
        x = np.array([0, 1]) + (-0.018 if group == "treated" else 0.018)
        ax.errorbar(
            x,
            g.net,
            yerr=[g.net - g.lower, g.upper - g.net],
            fmt="o-",
            color=color,
            label=label,
            capsize=4,
            lw=2,
            ms=8,
        )
    ax.set_xticks([0, 1], ["Prior 60 seconds", "Following 60 seconds"])
    ax.set_xlim(-0.2, 1.2)
    ax.axhline(0, color=LIGHT)
    ax.set_ylabel("Spurs points minus opponent points")
    ax.set_title("Both matched groups recover from the scoring dip", loc="left", pad=18)
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    save(
        fig,
        "timeout_rebound",
        f'{meta["matched_timeouts"]} timeouts in {meta["matched_games"]} games. Exact match on prior-minute net scoring; 95% game-bootstrap intervals.',
    )
    d = pd.read_csv(ROOT / "results/timeout_sensitivity.csv")
    fig, ax = plt.subplots(figsize=(10, 4.8))
    fig.subplots_adjust(left=0.3, right=0.96, bottom=0.24, top=0.82)
    for i, (_, v) in enumerate(d.iterrows()):
        ax.errorbar(
            v.estimate,
            i,
            xerr=[[v.estimate - v.lower], [v.upper - v.estimate]],
            fmt="o",
            capsize=4,
            ms=7,
            color=BLACK,
        )
        ax.text(
            v.estimate,
            i + 0.19,
            f"{int(v.timeouts)} matched timeouts",
            ha="center",
            va="top",
            fontsize=9,
        )
    ax.set_yticks(
        range(3), ["Exact prior-minute score", "Within 1 point", "Within 2 points"]
    )
    ax.set_ylim(2.45, -0.5)
    ax.axvline(0, color=LIGHT)
    ax.set_xlabel("Timeout minus comparison: net points in the next minute")
    ax.set_title(
        "No clear scoring advantage in the matched samples", loc="left", pad=18
    )
    save(
        fig,
        "timeout_sensitivity",
        "All matches are within the same game and quarter, with score and clock limits. Bars: 95% game-bootstrap intervals.",
    )
    d = pd.read_csv(ROOT / "results/timeout_balance.csv")
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    fig.subplots_adjust(left=0.30, right=0.96, bottom=0.24, top=0.82)
    for name, color, label, offset in [
        ("before", SILVER, "Before matching", -0.08),
        ("after", TEAL, "After exact-score matching", 0.08),
    ]:
        ax.scatter(d[name], np.arange(3) + offset, color=color, s=65, label=label)
    ax.set_yticks(
        range(3),
        ["Prior-minute net scoring", "Current score margin", "Seconds left in quarter"],
    )
    ax.invert_yaxis()
    ax.axvline(0, color=LIGHT)
    ax.set_xlabel("Mean difference / candidate-sample standard deviation")
    ax.set_title(
        "Check the starting conditions before reading the result", loc="left", pad=18
    )
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    ax.set_ylim(2.8, -0.5)
    save(
        fig,
        "timeout_balance",
        "Timeout group minus comparison group. Balance improves on observed variables; personnel and intent remain unmeasured.",
    )
    d = pd.read_csv(ROOT / "results/quarter_groups.csv")
    fig, ax = plt.subplots(figsize=(9.5, 5))
    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.26, top=0.82)
    x = np.arange(3)
    ax.errorbar(
        x,
        d.return_rate,
        yerr=[d.return_rate - d.lower, d.upper - d.return_rate],
        fmt="o",
        color=TEAL,
        capsize=6,
        ms=10,
    )
    for i, (_, v) in enumerate(d.iterrows()):
        ax.text(
            i,
            v.upper + 0.06,
            f"{v.return_rate:.0%}\n{int(v.attempts)} quarters",
            ha="center",
            fontsize=10,
        )
    ax.set_xticks(x, d.clock_band.str.replace(" seconds", ""))
    ax.set_ylim(0, 1.08)
    ax.set_xlim(-0.4, 2.4)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_ylabel("Share with a later Spurs return attempt")
    ax.set_xlabel("Seconds remaining at the first Spurs attempt in the 20–40s window")
    ax.set_title(
        "More time is associated with another trip to a shot", loc="left", pad=18
    )
    save(
        fig,
        "quarter_return",
        "Quarters 1–3 only. A return attempt follows an intervening opponent offensive event. Bars: 95% game-bootstrap intervals.",
    )
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.3, top=0.80, wspace=0.32)
    for ax, y, lo, hi, title, color in [
        (
            axes[0],
            "first_ppa",
            "first_low",
            "first_high",
            "Field-goal points on the index shot",
            BLACK,
        ),
        (
            axes[1],
            "closing_net",
            "net_lower",
            "net_upper",
            "Net points through quarter end",
            TEAL,
        ),
    ]:
        ax.errorbar(
            x,
            d[y],
            yerr=[d[y] - d[lo], d[hi] - d[y]],
            fmt="o",
            capsize=5,
            ms=8,
            color=color,
        )
        ax.set_xticks(x, ["20–<28s", "28–<34s", "34–40s"])
        ax.set_xlim(-0.4, 2.4)
        ax.axhline(0, color=LIGHT)
        ax.set_title(title, loc="left", fontsize=12, pad=18)
        ax.set_ylabel("Points")
        ax.set_xlabel("Clock at index attempt")
    save(
        fig,
        "quarter_tradeoff",
        "Different shot and game situations enter each band. Closing net includes free throws; these are observational comparisons.",
    )
    curve = pd.read_csv(ROOT / "results/quarter_prediction_curve.csv")
    held = pd.read_csv(ROOT / "results/quarter_holdout.csv")
    meta = json.loads((ROOT / "results/quarter_summary.json").read_text())
    fig, ax = plt.subplots(figsize=(9.5, 5))
    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.25, top=0.82)
    ax.plot(
        curve.seconds,
        curve.return_probability,
        color=TEAL,
        lw=2,
        label="Early-season model: tied game, Q2",
    )
    for band, g in held.groupby("clock_band"):
        value, lo, hi = mean_ci(g, "return_attempt")
        ax.errorbar(
            g.seconds.mean(),
            value,
            yerr=[[value - lo], [hi - value]],
            fmt="o",
            ms=7,
            capsize=4,
            color=ORANGE,
        )
    ax.scatter(
        [], [], color=ORANGE, label="Later clock bands: raw averages, 95% intervals"
    )
    ax.axhline(
        meta["training_return_rate"],
        color=SILVER,
        ls="--",
        label="Early-season constant baseline",
    )
    ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_xlabel("Seconds remaining at the index attempt")
    ax.set_ylabel("Return-attempt probability")
    ax.set_title(
        "The clock model gets a separate later-season test", loc="left", pad=18
    )
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(
        fig,
        "quarter_forecast",
        f'{meta["training_quarters"]} training quarters; {meta["test_quarters"]} later quarters. Model log loss {meta["model_logloss"]:.3f}; baseline {meta["baseline_logloss"]:.3f}. Lower is better.',
    )
    return 9


if __name__ == "__main__":
    print(run(), "figures exported")
