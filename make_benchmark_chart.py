"""Render assets/wiki_benchmark.png from benchmark_results.json.

Horizontal bars, two panels: score out of 100 (with 95% intervals) and token
cost per answer at list price. The wiki analyst on the small model is the
highlighted row. Run after benchmark.py, from the project root.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
HIGHLIGHT = "#2a78d6"  # categorical slot 1
BAR_GRAY = "#898781"

results = json.loads(Path("benchmark_results.json").read_text(encoding="utf-8"))
token_costs = json.loads(Path("benchmark_token_costs.json").read_text(encoding="utf-8"))

ROWS = [  # top to bottom; (arm, label, highlighted)
    ("haiku-wiki", "Claude Haiku 5.5\nfrom the wiki", True),
    ("haiku-raw", "Claude Haiku 5.5\nsearching the raw documents", False),
    ("sonnet-wiki", "Claude Sonnet 5.5\nfrom the wiki", False),
    ("sonnet-raw", "Claude Sonnet 5.5\nsearching the raw documents", False),
]

scores = [results["summary"][a]["score_mean"] for a, _, _ in ROWS]
cis = [results["summary"][a]["score_ci95"] for a, _, _ in ROWS]
costs = [token_costs[a]["mean"] for a, _, _ in ROWS]
colors = [HIGHLIGHT if hl else BAR_GRAY for _, _, hl in ROWS]
y = range(len(ROWS))[::-1]  # first row on top

fig, (ax1, ax2) = plt.subplots(
    1, 2, figsize=(10.4, 4.45), dpi=200, width_ratios=[1.15, 1]
)
fig.patch.set_facecolor(SURFACE)
plt.rcParams["font.family"] = "DejaVu Sans"

for ax in (ax1, ax2):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.tick_params(colors=MUTED, length=0, labelsize=9)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_yticks(list(y))

# --- Score panel ---
ax1.barh(list(y), scores, height=0.55, color=colors)
ax1.errorbar(
    scores, list(y), xerr=cis, fmt="none",
    ecolor=INK, elinewidth=1.2, capsize=3, capthick=1.2,
)
for yi, s, ci, (_, _, hl) in zip(y, scores, cis, ROWS):
    ax1.text(s + ci + 2.5, yi, f"{s:.1f} ± {ci:.1f}", va="center",
             fontsize=10.5, color=INK, fontweight="bold" if hl else "normal")
labels = [lbl for _, lbl, _ in ROWS]
ax1.set_yticklabels(labels, fontsize=10, color=INK_2)
for tick, (_, _, hl) in zip(ax1.get_yticklabels(), ROWS):
    if hl:
        tick.set_color(HIGHLIGHT)
        tick.set_fontweight("bold")
ax1.set_xlim(0, 118)
ax1.set_xticks([0, 25, 50, 75, 100])
ax1.set_title("Score, out of 100 (± 95% interval)",
              fontsize=11.5, color=INK, fontweight="bold", pad=10)

# --- Cost panel ---
ax2.barh(list(y), costs, height=0.55, color=colors)
for yi, c, (_, _, hl) in zip(y, costs, ROWS):
    ax2.text(c + max(costs) * 0.035, yi, f"${c:.4f}", va="center",
             fontsize=10.5, color=INK, fontweight="bold" if hl else "normal")
ax2.set_yticklabels([])
ax2.set_xlim(0, max(costs) * 1.3)
ax2.set_title("Token cost per answer, list price",
              fontsize=11.5, color=INK, fontweight="bold", pad=10)
from matplotlib.ticker import FuncFormatter
ax2.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.3f}"))

fig.suptitle(
    "On six pamphlets, wiki and raw-document analysts score the same",
    x=0.015, y=0.985, ha="left", fontsize=15, color=INK, fontweight="bold",
)
fig.text(
    0.015, 0.905,
    "Every arm within each other's 95% intervals; the wiki's edge shows on the "
    "cross-pamphlet question (≈95 vs ≈70)",
    fontsize=10.5, color=INK_2,
)
fig.text(
    0.015, 0.015,
    "10 questions with answer keys over 2 runs each. Score: mean of two judge "
    "models ± the 95% interval. Cost: the session's tokens at list price. "
    "November 8, 2026.",
    fontsize=8.5, color=MUTED,
)
fig.subplots_adjust(left=0.21, right=0.985, top=0.78, bottom=0.17, wspace=0.08)
fig.savefig("assets/wiki_benchmark.png", facecolor=SURFACE)
print("wrote assets/wiki_benchmark.png")
