import datetime
import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from bot.config import PLAYER_CODES

# Chart chrome, taken from the categorical/ink reference palette (light mode —
# Telegram renders photos on a fixed light card regardless of chat theme).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

# Fixed hue order (slots 1-5): blue, orange, aqua, yellow, magenta.
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]

LABEL_MIN_GAP_PX = 15
LABEL_OFFSET_PX = 8


def render_standings_chart(year: int, weekly_scores: dict[str, list[tuple[str, int]]]) -> bytes:
    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    end_points = []  # (code, x_num, y, color) — last plotted point of each series
    for i, code in enumerate(PLAYER_CODES):
        points = weekly_scores.get(code) or []
        if not points:
            continue
        color = CATEGORICAL[i % len(CATEGORICAL)]
        dates = [datetime.date.fromisoformat(d) for d, _ in points]
        scores = [s for _, s in points]

        ax.plot(
            dates,
            scores,
            color=color,
            linewidth=2,
            marker="o",
            markersize=6,
            markerfacecolor=color,
            markeredgecolor=SURFACE,
            markeredgewidth=1.5,
            solid_capstyle="round",
            solid_joinstyle="round",
            label=code,
            zorder=3,
        )
        end_points.append((code, mdates.date2num(dates[-1]), scores[-1], color))

    ax.set_title(
        f"Puntajes Flashback {year}",
        fontsize=14,
        fontweight="bold",
        color=INK_PRIMARY,
        loc="left",
        pad=14,
    )

    ax.grid(True, axis="y", color=GRID, linewidth=1, zorder=0)
    ax.grid(False, axis="x")
    for name, spine in ax.spines.items():
        if name == "bottom":
            spine.set_color(BASELINE)
            spine.set_linewidth(1)
        else:
            spine.set_visible(False)

    ax.tick_params(axis="x", colors=INK_MUTED, labelsize=9, length=0)
    ax.tick_params(axis="y", colors=INK_MUTED, labelsize=9, length=0)

    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=5, maxticks=10))
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    ax.margins(x=0.02)

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=len(PLAYER_CODES),
        frameon=False,
        fontsize=10,
        labelcolor=INK_SECONDARY,
        handlelength=1.5,
    )

    # Reserve space on the right for direct end-labels, independent of the
    # data range, since decluttering can push labels outside the plotted area.
    fig.tight_layout(rect=(0, 0, 0.87, 1))

    _draw_end_labels(fig, ax, end_points)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def _draw_end_labels(fig, ax, end_points: list[tuple[str, float, int, str]]) -> None:
    if not end_points:
        return

    # Finalize transforms before reading pixel positions.
    fig.canvas.draw()

    transformed = []
    for code, x_num, y, color in end_points:
        px, py = ax.transData.transform((x_num, y))
        transformed.append([code, x_num, y, px, py])
    transformed.sort(key=lambda t: t[4])  # ascending pixel y

    adjusted_py = []
    prev = None
    for t in transformed:
        py = t[4]
        if prev is not None and py - prev < LABEL_MIN_GAP_PX:
            py = prev + LABEL_MIN_GAP_PX
        adjusted_py.append(py)
        prev = py

    inv = ax.transData.inverted()
    for (code, x_num, y, px, orig_py), new_py in zip(transformed, adjusted_py):
        label_px = px + LABEL_OFFSET_PX
        label_x, label_y = inv.transform((label_px, new_py))

        if abs(new_py - orig_py) > 2:
            ax.plot(
                [x_num, label_x],
                [y, label_y],
                color=INK_MUTED,
                linewidth=0.8,
                zorder=2,
                clip_on=False,
            )

        ax.text(
            label_x,
            label_y,
            code,
            va="center",
            ha="left",
            fontsize=10,
            fontweight="bold",
            color=INK_PRIMARY,
            clip_on=False,
            zorder=4,
        )
