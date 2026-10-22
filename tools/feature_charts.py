"""Rebuild the turnover comparison: python -m tools.feature_charts."""
from pathlib import Path
import pandas as pd
from .chart_style import canvas, finish, stat, note, tidy, ORANGE, TEAL, MUTED, GRID

ROOT = Path(__file__).resolve().parents[1]


def main():
    d = pd.read_csv(ROOT / "results/turnover_adjusted.csv").query("seconds == 12").reset_index(drop=True)
    labels = ["All eligible turnovers", "Competitive score / clock", "No timeout in next 12 seconds"]
    fig = canvas("03 / Transition defense", "The next 12 seconds make turnover type matter",
                 "Spurs, 2025–26 · opponent points after steal-linked turnovers minus other turnovers")
    ax = fig.add_axes([.315, .275, .38, .42])
    for i, r in d.iterrows():
        color = ORANGE if i == 0 else TEAL
        ax.hlines(i, r.lower, r.upper, color=color, lw=3)
        ax.scatter(r.estimate, i, color=color, s=100, zorder=3)
        ax.text(r.estimate, i-.26, f"{r.estimate:+.2f}", ha="center", color=color, fontsize=17, weight="bold")
        ax.text(r.estimate, i+.26, f"{int(r.events):,} turnovers · {int(r.games)} games", ha="center", color=MUTED, fontsize=10)
    ax.set_yticks(range(3), labels)
    ax.set_ylim(2.65, -.6)
    ax.set_xlim(-.025, .98)
    ax.set_xticks([0, .2, .4, .6, .8])
    ax.axvline(0, color=GRID)
    ax.set_xlabel("Adjusted opponent points per turnover", labelpad=14)
    tidy(ax)
    stat(fig, .77, .68, f"{d.iloc[0].estimate:+.2f}", "points in the main comparison", color=ORANGE)
    note(fig, .77, .56, "A useful review priority", "Examine ball security, floor balance and the first recovery action after a live-ball loss.", width=29)
    note(fig, .77, .34, "Not a policy effect", "The model does not tell us how many points a new coaching rule would save. Steal linkage is a recorded proxy.", width=29)
    finish(fig, ROOT / "figures/turnover_adjusted",
           "Source: results/turnover_adjusted.csv · Scoring window includes free throws; main sample: 582 steal-linked, 425 other turnovers.",
           "Game fixed effects with score, clock and period controls. Lines: 95% game-cluster bootstrap intervals; samples overlap.")


if __name__ == "__main__":
    main()
