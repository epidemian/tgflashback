import collections
import datetime
import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
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

BAR_SLOT_WIDTH = 0.72
WEEK_WIDTH_IN = 0.42  # figure inches per week
MAX_FIG_WIDTH_IN = 32
MIN_SEGMENT_HEIGHT_FOR_LABEL = 1.5  # score points; thinner segments skip the code label


def _text_color(hex_color: str) -> str:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return INK_PRIMARY if luminance > 140 else "#ffffff"


def _stack_segments(
    entries: list[tuple[str, int]],
) -> list[tuple[str, float, float, float, float, int]]:
    """Lay out a week's scores as bands on a shared 0..max(score) axis: each
    band spans from the previous (lower) score up to this player's own score,
    so a band's top edge is that player's real score, not a running sum.
    Ties share a band, split side by side instead of stacked."""
    ordered = sorted(entries, key=lambda ce: ce[1])
    groups: list[tuple[int, list[str]]] = []
    for code, score in ordered:
        if groups and groups[-1][0] == score:
            groups[-1][1].append(code)
        else:
            groups.append((score, [code]))

    segments = []
    prev_score = 0.0
    for score, codes in groups:
        height = score - prev_score
        seg_width = BAR_SLOT_WIDTH / len(codes)
        for j, code in enumerate(codes):
            x0 = -BAR_SLOT_WIDTH / 2 + j * seg_width
            segments.append((code, x0, seg_width, prev_score, height, len(codes)))
        prev_score = score
    return segments


def _bucket_by_iso_week(
    weekly_scores: dict[str, list[tuple[str, int]]],
) -> tuple[list[str], dict[str, dict[str, int]]]:
    # Editions are normally exactly 7 days apart, so grouping by ISO
    # (year, week) is a no-op for the common case. It only kicks in when a
    # player's score lands a day or two off from the rest of the group (e.g.
    # they solved a different day's puzzle), which would otherwise show up
    # as its own near-empty column next to the real one for that week.
    week_dates: dict[tuple[int, int], collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for points in weekly_scores.values():
        for puzzle_date, _ in points:
            iso_year, iso_week, _ = datetime.date.fromisoformat(puzzle_date).isocalendar()
            week_dates[(iso_year, iso_week)][puzzle_date] += 1

    representative_date = {
        week_key: min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        for week_key, counts in week_dates.items()
    }

    dates = [representative_date[k] for k in sorted(representative_date)]

    scores_by_date: dict[str, dict[str, int]] = {code: {} for code in PLAYER_CODES}
    for code, points in weekly_scores.items():
        for puzzle_date, score in points:
            iso_key = datetime.date.fromisoformat(puzzle_date).isocalendar()[:2]
            scores_by_date[code][representative_date[iso_key]] = score

    return dates, scores_by_date


def render_standings_chart(year: int, weekly_scores: dict[str, list[tuple[str, int]]]) -> bytes:
    dates, scores_by_date = _bucket_by_iso_week(weekly_scores)

    fig_width = min(MAX_FIG_WIDTH_IN, max(9.0, len(dates) * WEEK_WIDTH_IN))
    fig, ax = plt.subplots(figsize=(fig_width, 5), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    color_by_code = {code: CATEGORICAL[i % len(CATEGORICAL)] for i, code in enumerate(PLAYER_CODES)}

    for idx, d in enumerate(dates):
        entries = [
            (code, scores_by_date[code][d]) for code in PLAYER_CODES if d in scores_by_date[code]
        ]
        for code, x0, seg_width, y0, height, tie_count in _stack_segments(entries):
            color = color_by_code[code]
            ax.bar(
                idx + x0 + seg_width / 2,
                height,
                width=seg_width * 0.96,
                bottom=y0,
                color=color,
                edgecolor=SURFACE,
                linewidth=1,
                zorder=3,
            )
            # A 3+ way tie splits the band too thin for a legible label; the
            # legend + color still identify who's who.
            fontsize = {1: 7.5, 2: 6.5}.get(tie_count)
            if fontsize and height >= MIN_SEGMENT_HEIGHT_FOR_LABEL:
                ax.text(
                    idx + x0 + seg_width / 2,
                    y0 + height / 2,
                    code,
                    ha="center",
                    va="center",
                    fontsize=fontsize,
                    fontweight="bold",
                    color=_text_color(color),
                    zorder=4,
                )

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

    # Only label the first week of each month, else the x-axis is just as
    # cluttered as the old line chart was.
    tick_positions = []
    tick_labels = []
    last_month = None
    for idx, d in enumerate(dates):
        month = datetime.date.fromisoformat(d).month
        if month != last_month:
            tick_positions.append(idx)
            tick_labels.append(datetime.date.fromisoformat(d).strftime("%b"))
            last_month = month
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels)
    ax.set_xlim(-0.5, len(dates) - 0.5)

    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))

    legend_handles = [Patch(facecolor=color_by_code[code], label=code) for code in PLAYER_CODES]
    ax.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        ncol=len(PLAYER_CODES),
        frameon=False,
        fontsize=10,
        labelcolor=INK_SECONDARY,
        handlelength=1.5,
    )

    fig.tight_layout(rect=(0, 0, 1, 1))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=SURFACE)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
