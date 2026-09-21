"""Chart the naive baseline's cost -- split into input vs. output, never a
single token-count line. Input and output are priced differently (Haiku 4.5:
$1/MTok in, $5/MTok out), so lumping them into one number hides which one is
actually driving the bill.
"""

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from contextlab import config

# Validated categorical pair (dataviz skill palette, slots 1-2; passes CVD +
# normal-vision separation checks at light-surface contrast).
COLOR_INPUT = "#2a78d6"
COLOR_OUTPUT = "#eb6834"
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"


def load_runs(path):
    with open(path) as f:
        return [json.loads(line) for line in f]


def plot_cost_chart(runs, out_path, title):
    ids = [r["id"] for r in runs]
    input_costs = [r["input_cost"] for r in runs]
    output_costs = [r["output_cost"] for r in runs]
    total_cost = sum(input_costs) + sum(output_costs)

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    x = range(len(ids))
    bar_width = 0.55

    ax.bar(x, input_costs, width=bar_width, color=COLOR_INPUT, label="Input cost",
           edgecolor=SURFACE, linewidth=1.5)
    ax.bar(x, output_costs, width=bar_width, bottom=input_costs, color=COLOR_OUTPUT,
           label="Output cost", edgecolor=SURFACE, linewidth=1.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(ids, color=INK_SECONDARY, fontsize=9)
    ax.set_ylabel("Cost per request ($)", color=INK_MUTED, fontsize=10)
    ax.tick_params(axis="y", colors=INK_MUTED, labelsize=9)

    fig.suptitle(title, x=0.02, y=0.985, ha="left", color=INK_PRIMARY,
                 fontsize=13, fontweight="bold")
    fig.text(0.02, 0.925, f"Total: ${total_cost:.4f}  ·  input ${sum(input_costs):.4f}"
             f"  +  output ${sum(output_costs):.4f}",
             ha="left", color=INK_SECONDARY, fontsize=9.5)

    ax.grid(axis="y", color=GRIDLINE, linewidth=1, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRIDLINE)

    ax.legend(frameon=False, loc="upper right", labelcolor=INK_SECONDARY, fontsize=9.5)

    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(out_path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Wrote {out_path}")
    print(f"Total cost: ${total_cost:.6f}  (input ${sum(input_costs):.6f}"
          f" + output ${sum(output_costs):.6f})")


if __name__ == "__main__":
    runs_path = config.RESULTS_DIR / "naive_runs_haiku.jsonl"
    runs = load_runs(runs_path)
    plot_cost_chart(
        runs,
        config.RESULTS_DIR / "cost_chart_phase0.png",
        "Phase 0 naive baseline — cost per request (Claude Haiku 4.5)",
    )
