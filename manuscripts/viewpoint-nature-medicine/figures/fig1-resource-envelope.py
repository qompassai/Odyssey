"""Generate Figure 1 of the Nature Medicine Comment "Small Is Beautiful".

Purpose: draw the resource-envelope schematic (one large model versus a
three-seat small-model team, plus the authority rule) as a static SVG.

Contract:
- Every number drawn comes from the constants below, and each constant names
  the line of the Kintsugi tiny-tier run record it was copied from.
- With --source, the run record is read (bounded), its sha256 must equal
  SOURCE_SHA256, and every anchor string must appear in it; otherwise
  SourceMismatchError is raised and nothing is written.
- The output path must not already exist (exclusive create), so an earlier
  figure is never overwritten in place.
- Pure standard library; runs identically under python and python -O.
- Output is deterministic: same inputs, same bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

# Source record (primo): ~/workspace/phlow-trials/tiny-20261017/RESULTS.md
SOURCE_SHA256 = "1e1bb52a6495b07ccec3b3836454384a7df08cc538eff42458df3442501e6869"
SOURCE_MAX_BYTES = 1_000_000
OUTPUT_MAX_BYTES = 200_000

# Anchor strings that must appear verbatim in the source record.
SOURCE_ANCHORS: tuple[str, ...] = (
    "| hf-qwen3-coder-30b (incumbent) | 5 / 5 | 9 | 6 | 20 | 18.56 | not measured |",
    "| Qwen2.5-Coder-3B | 0 / 1 | 8 | 0† | 8 | 2.10 | not measured |",
    "| **Bonsai-8B Q1_0 (binary)** | 0 / 0 | 9 | 6 | **15** | 1.16 | 6.51 |",
    "| 3B + adapter | 20/20 | 1.000 | 1 | 1 | 18/20 |",
    "| Served RAW | 20/20 | 1.000 | 1 | 2 | 17/20 |",
    "f16, 29,968,576 B",
    "6/6 at 1.39 GiB RAM",
    "2.10 + 1.16 + 0.96 ≈ 4.2 GB",
    "23% of the single large model's file",
)

# Okabe-Ito colour-blind-safe palette.
COLOUR_LARGE = "#D55E00"  # vermillion
COLOUR_DIGEST = "#0072B2"  # blue
COLOUR_TRIAGE = "#E69F00"  # orange
COLOUR_TOOL = "#009E73"  # bluish green
COLOUR_INK = "#000000"
COLOUR_MUTED = "#555555"
COLOUR_PENDING = "#999999"

FONT_FAMILY = "Arial, Helvetica, sans-serif"
CANVAS_WIDTH_MM = 180
CANVAS_HEIGHT_MM = 118
BAR_ORIGIN_X_MM = 42.0
BAR_SCALE_MM_PER_GB = 7.0
BAR_HEIGHT_MM = 7.0

LARGE_FILE_GB = 18.56  # RESULTS.md section 11.2 table, hf-qwen3-coder-30b row
LARGE_POINTS_OF_24 = 20  # same row
TEAM_TOTAL_LABEL = "≈4.2 GB, 23% of the large file"  # RESULTS.md section 11.4


class SourceMismatchError(Exception):
    """The run record on disk is not the one these constants were copied from."""


@dataclass(frozen=True)
class Seat:
    name: str
    model: str
    file_gb: float
    file_label: str
    result_label: str
    cpu_peak_label: str
    colour: str


SEATS: tuple[Seat, ...] = (
    Seat(  # RESULTS.md 4.x pilot tables and section 11.2 Qwen2.5-Coder-3B row
        name="Digest seat",
        model="Qwen2.5-Coder-3B + low-rank adapter (30 MB)",
        file_gb=2.10,
        file_label="2.10 GB file",
        result_label="Clean held-out digests 18/20 (17/20 served)",
        cpu_peak_label="CPU-only peak memory: not measured",
        colour=COLOUR_DIGEST,
    ),
    Seat(  # RESULTS.md section 11.2 Bonsai-8B Q1_0 row
        name="Triage seat",
        model="Bonsai-8B Q1_0 (1-bit)",
        file_gb=1.16,
        file_label="1.16 GB file",
        result_label="Triage labels 9/12",
        cpu_peak_label="CPU-only peak memory 6.51 GiB",
        colour=COLOUR_TRIAGE,
    ),
    Seat(  # RESULTS.md section 11.4 tool seat
        name="Tool seat",
        model="LFM2.5-1.2B",
        file_gb=0.96,
        file_label="0.96 GB file",
        result_label="Parsed tool calls 6/6",
        cpu_peak_label="CPU-only peak memory 1.39 GiB",
        colour=COLOUR_TOOL,
    ),
)


def verify_source(source_path: Path) -> None:
    """Raise SourceMismatchError unless the record matches hash and anchors."""
    size_bytes = source_path.stat().st_size
    if size_bytes > SOURCE_MAX_BYTES:
        raise SourceMismatchError(f"source too large: {size_bytes} bytes")
    with source_path.open("rb") as handle:
        data = handle.read(SOURCE_MAX_BYTES + 1)
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCE_SHA256:
        raise SourceMismatchError(f"sha256 {digest} != expected {SOURCE_SHA256}")
    text = data.decode("utf-8")
    for anchor in SOURCE_ANCHORS:
        if anchor not in text:
            raise SourceMismatchError(f"anchor not found in source: {anchor!r}")


def _text(x_mm: float, y_mm: float, body: str, *, size_mm: float = 2.6,
          weight: str = "normal", fill: str = COLOUR_INK, anchor: str = "start") -> str:
    return (
        f'<text x="{x_mm:.2f}" y="{y_mm:.2f}" font-size="{size_mm:.2f}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(body)}</text>'
    )


def _rect(x_mm: float, y_mm: float, w_mm: float, h_mm: float, *, fill: str,
          stroke: str = "none", dashed: bool = False) -> str:
    dash = ' stroke-dasharray="1.2,0.8"' if dashed else ""
    return (
        f'<rect x="{x_mm:.2f}" y="{y_mm:.2f}" width="{w_mm:.2f}" height="{h_mm:.2f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="0.3"{dash}/>'
    )


def panel_a() -> list[str]:
    """Files on disk, drawn to scale."""
    parts = [_text(4, 7, "a", size_mm=4.0, weight="bold"),
             _text(10, 7, "Files on disk, drawn to scale (1 GB = 7 mm)", size_mm=3.0,
                   weight="bold")]
    large_w = LARGE_FILE_GB * BAR_SCALE_MM_PER_GB
    parts.append(_text(4, 16.5, "One large model", weight="bold"))
    parts.append(_rect(BAR_ORIGIN_X_MM, 12, large_w, BAR_HEIGHT_MM, fill=COLOUR_LARGE))
    parts.append(_text(BAR_ORIGIN_X_MM + 2, 16.6, "Large coding model, 18.56 GB file",
                       fill="#FFFFFF", weight="bold"))
    parts.append(_text(BAR_ORIGIN_X_MM, 22.5,
                       f"{LARGE_POINTS_OF_24}/24 points on the non-clinical battery; "
                       "served on a workstation GPU; CPU-only memory not measured",
                       size_mm=2.3, fill=COLOUR_MUTED))
    parts.append(_text(4, 31.5, "Three-seat team", weight="bold"))
    x_mm = BAR_ORIGIN_X_MM
    for seat in SEATS:
        width_mm = seat.file_gb * BAR_SCALE_MM_PER_GB
        parts.append(_rect(x_mm, 27, width_mm, BAR_HEIGHT_MM, fill=seat.colour))
        x_mm += width_mm
    parts.append(_text(x_mm + 2, 31.6, TEAM_TOTAL_LABEL, weight="bold"))
    pending_x_mm, pending_w_mm = 118.0, 58.0
    pending_mid_mm = pending_x_mm + pending_w_mm / 2
    assert pending_x_mm + pending_w_mm <= CANVAS_WIDTH_MM
    parts.append(_rect(pending_x_mm, 26.5, pending_w_mm, 8, fill="none",
                       stroke=COLOUR_PENDING, dashed=True))
    parts.append(_text(pending_mid_mm, 30.0, "Team production vs large model:",
                       size_mm=2.3, fill=COLOUR_MUTED, anchor="middle"))
    parts.append(_text(pending_mid_mm, 33.4, "RESULTS PENDING", size_mm=2.6, weight="bold",
                       fill=COLOUR_MUTED, anchor="middle"))
    return parts


def panel_b() -> list[str]:
    """One card per seat, with measured result and CPU-only peak memory."""
    parts = [_text(4, 46, "b", size_mm=4.0, weight="bold"),
             _text(10, 46, "Seats filled by measured production per unit cost",
                   size_mm=3.0, weight="bold")]
    card_w_mm, card_h_mm, gap_mm = 56.0, 26.0, 3.0
    for index, seat in enumerate(SEATS):
        x_mm = 4 + index * (card_w_mm + gap_mm)
        parts.append(_rect(x_mm, 50, card_w_mm, card_h_mm, fill="#FFFFFF", stroke=seat.colour))
        parts.append(_rect(x_mm, 50, card_w_mm, 4.5, fill=seat.colour))
        parts.append(_text(x_mm + 2, 53.4, seat.name, fill="#FFFFFF", weight="bold"))
        lines = (seat.model, seat.file_label, seat.result_label, seat.cpu_peak_label)
        for line_index, line in enumerate(lines):
            parts.append(_text(x_mm + 2, 59.5 + line_index * 4.4, line, size_mm=2.4))
    return parts


def panel_c() -> list[str]:
    """Authority rule: models propose, the record checks, the clinician decides."""
    parts = [_text(4, 87, "c", size_mm=4.0, weight="bold"),
             _text(10, 87, "Authority stays where it can be checked", size_mm=3.0,
                   weight="bold")]
    steps = ("Models propose", "Deterministic record checks", "Clinician decides")
    box_w_mm, box_h_mm, gap_mm = 46.0, 10.0, 13.0
    for index, label in enumerate(steps):
        x_mm = 4 + index * (box_w_mm + gap_mm)
        parts.append(_rect(x_mm, 91, box_w_mm, box_h_mm, fill="#F2F2F2", stroke=COLOUR_INK))
        parts.append(_text(x_mm + box_w_mm / 2, 97.2, label, size_mm=2.8, weight="bold",
                           anchor="middle"))
        if index + 1 < len(steps):
            start_mm = x_mm + box_w_mm + 1.5
            end_mm = start_mm + gap_mm - 3.0
            parts.append(f'<line x1="{start_mm:.2f}" y1="96" x2="{end_mm:.2f}" y2="96" '
                         f'stroke="{COLOUR_INK}" stroke-width="0.5" marker-end="url(#arrow)"/>')
    parts.append(_text(4, 108, "If the record or the serving endpoint fails, the model layer "
                       "fails closed. Models never commit an action.", size_mm=2.4,
                       fill=COLOUR_MUTED))
    parts.append(_text(4, 113.5, "All measurements: non-clinical coordination battery, one "
                       "workstation, 17 October 2026. Clinical battery: RESULTS PENDING.",
                       size_mm=2.4, fill=COLOUR_MUTED))
    return parts


def render_svg() -> str:
    """Return the complete SVG document as text."""
    head = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_WIDTH_MM}mm" '
        f'height="{CANVAS_HEIGHT_MM}mm" viewBox="0 0 {CANVAS_WIDTH_MM} {CANVAS_HEIGHT_MM}" '
        f'font-family="{FONT_FAMILY}" role="img" aria-labelledby="fig-title fig-desc">\n'
        '<title id="fig-title">Figure 1. The resource envelope, seat by seat</title>\n'
        '<desc id="fig-desc">Panel a compares file sizes drawn to scale: one large model '
        'at 18.56 GB against a three-seat team totalling about 4.2 GB. Panel b lists each '
        'seat with its measured result and CPU-only peak memory. Panel c shows the '
        'authority rule: models propose, a deterministic record checks, a clinician '
        'decides.</desc>\n'
        '<defs><marker id="arrow" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="4" '
        'markerHeight="4" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#000000"/>'
        '</marker></defs>\n'
        f'<rect x="0" y="0" width="{CANVAS_WIDTH_MM}" height="{CANVAS_HEIGHT_MM}" '
        'fill="#FFFFFF"/>\n'
    )
    body = "\n".join(panel_a() + panel_b() + panel_c())
    return head + body + "\n</svg>\n"


def write_exclusive(output_path: Path, document: str) -> None:
    """Create output_path; refuse to overwrite. Partial file is removed on error."""
    data = document.encode("utf-8")
    if len(data) > OUTPUT_MAX_BYTES:
        raise ValueError(f"SVG too large: {len(data)} bytes")
    with output_path.open("xb") as handle:
        handle.write(data)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output", type=Path, help="SVG path to create (must not exist)")
    parser.add_argument("--source", type=Path, default=None,
                        help="run record to verify the constants against")
    args = parser.parse_args(argv)
    if args.source is not None:
        verify_source(args.source)
    write_exclusive(args.output, render_svg())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
