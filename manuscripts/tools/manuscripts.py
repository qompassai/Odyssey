#!/usr/bin/env python3
"""manuscripts.py — Odyssey manuscript sub-repo CLI (scaffold/status/rollup/tracker).

Contract:
  - status.json is the single source of truth per manuscript
    (schema: slug, title, journal_name, profile_key, stage, updated, history).
  - stage must be one of STAGES; anything else is a hard error.
  - All writes are atomic (temp file + rename) and never clobber an
    existing status.json or NOTES.md during scaffold.
  - rollup fails loudly on any malformed status.json; it never
    silently skips a manuscript.
  - check/package/submit are NOT in this slice: they land with the
    journal-profile step and the Playwright step of the program brief.

Usage:
  manuscripts.py scaffold <slug> --root DIR --seeds seeds.json
  manuscripts.py status <slug> <stage> --root DIR [--note TEXT]
  manuscripts.py rollup --root DIR [--out FILE]
  manuscripts.py tracker --root DIR [--out FILE]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

STAGES = [
    "planned",
    "drafting",
    "internal-review",
    "preflight",
    "packaged",
    "submitted",
    "under-review",
    "revision",
    "accepted",
    "published",
    "withdrawn",
]

REQUIRED_KEYS = ["slug", "title", "journal_name", "profile_key", "stage", "updated", "history"]
SUBDIRS = ["manuscript", "figures", "submission"]
LIFECYCLE_STAGES = STAGES[:-1]
PROGRESS_BAR_CELLS = 10
SHARE_BAR_CELLS = 20
STAGE_ICONS = {
    "accepted": "✅",
    "drafting": "✍️",
    "internal-review": "🔎",
    "packaged": "📦",
    "planned": "⚪",
    "preflight": "🧪",
    "published": "🎉",
    "revision": "🔁",
    "submitted": "📨",
    "under-review": "👀",
    "withdrawn": "⛔",
}


def fail(message: str) -> "SystemExit":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def today() -> str:
    return date.today().isoformat()


def atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_json(path: Path, data: object) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_status(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path}: unreadable or invalid JSON ({exc})")
    for key in REQUIRED_KEYS:
        if key not in data:
            fail(f"{path}: missing required key {key!r}")
    if data["stage"] not in STAGES:
        fail(f"{path}: stage {data['stage']!r} not in the stage enum")
    if not isinstance(data["history"], list):
        fail(f"{path}: history must be a list")
    return data


def cmd_scaffold(args: argparse.Namespace) -> None:
    root = Path(args.root)
    seeds = json.loads(Path(args.seeds).read_text(encoding="utf-8"))
    if args.slug not in seeds:
        fail(f"slug {args.slug!r} not present in seeds file {args.seeds}")
    seed = seeds[args.slug]
    target = root / args.slug
    for sub in SUBDIRS:
        (target / sub).mkdir(parents=True, exist_ok=True)
        keep = target / sub / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
    refs = target / "refs.bib"
    if not refs.exists():
        refs.write_text(f"% Bibliography for {args.slug} — entries land with drafting.\n", encoding="utf-8")
    status_path = target / "status.json"
    if status_path.exists():
        print(f"{args.slug}: status.json exists, left untouched")
    else:
        status = {
            "slug": args.slug,
            "title": seed["title"],
            "journal_name": seed["journal_name"],
            "profile_key": seed["profile_key"],
            "stage": "planned",
            "updated": today(),
            "history": [{"date": today(), "event": "Scaffolded from the approved slate seed"}],
        }
        atomic_write_json(status_path, status)
        print(f"{args.slug}: status.json seeded (stage=planned)")
    notes = target / "NOTES.md"
    if notes.exists():
        print(f"{args.slug}: NOTES.md exists, left untouched")
    else:
        notes.write_text(
            f"# {args.slug} — NOTES\n\n"
            f"Study: {seed['study']}. Target: {seed['journal_name']} "
            f"(profile `{seed['profile_key']}`).\n"
            f"Seeded {today()} from the approved slate (manuscript program brief). "
            "Decisions and correspondence land here; stage history lives in status.json.\n",
            encoding="utf-8",
        )
        print(f"{args.slug}: NOTES.md seeded")


def cmd_status(args: argparse.Namespace) -> None:
    if args.stage not in STAGES:
        fail(f"stage {args.stage!r} not in the stage enum: {', '.join(STAGES)}")
    status_path = Path(args.root) / args.slug / "status.json"
    if not status_path.exists():
        fail(f"{status_path}: no such status.json (scaffold first)")
    status = load_status(status_path)
    status["stage"] = args.stage
    status["updated"] = today()
    event = args.note if args.note else f"Stage set to {args.stage}"
    status["history"].append({"date": today(), "event": event})
    atomic_write_json(status_path, status)
    print(f"{args.slug}: stage={args.stage}")


def load_all_statuses(root: Path) -> list[dict]:
    statuses = []
    for status_path in sorted(root.glob("*/status.json")):
        statuses.append(load_status(status_path))
    if not statuses:
        fail(f"{root}: no status.json files found")
    return statuses


def cmd_rollup(args: argparse.Namespace) -> None:
    root = Path(args.root)
    entries = [
        {
            "slug": data["slug"],
            "title": data["title"],
            "journal_name": data["journal_name"],
            "stage": data["stage"],
            "updated": data["updated"],
        }
        for data in load_all_statuses(root)
    ]
    rollup = {"generated": today(), "source": "odyssey manuscripts rollup", "manuscripts": entries}
    out = Path(args.out) if args.out else root / "rollup.json"
    atomic_write_json(out, rollup)
    print(f"rollup: {len(entries)} manuscripts -> {out}")


def stage_label(stage: str) -> str:
    return stage.replace("-", " ").title()


def stage_progress(stage: str) -> int | None:
    if stage == "withdrawn":
        return None
    index = LIFECYCLE_STAGES.index(stage)
    return round(index * 100 / (len(LIFECYCLE_STAGES) - 1))


def render_bar(percent: float, cells: int) -> str:
    bounded_percent = max(0.0, min(100.0, percent))
    filled = int(round(bounded_percent * cells / 100))
    return "█" * filled + "░" * (cells - filled)


def markdown_cell(value: object) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ")
    return (
        text.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def tracker_sort_key(data: dict) -> tuple[int, str]:
    progress = stage_progress(data["stage"])
    rank = -1 if progress is None else LIFECYCLE_STAGES.index(data["stage"])
    return (-rank, str(data["slug"]))


def _distribution_rows(counts: dict[str, int], total: int) -> list[str]:
    rows = []
    for stage in STAGES:
        count = counts[stage]
        share = count * 100 / total
        rows.append(
            f"| {STAGE_ICONS[stage]} {stage_label(stage)} | {count} | "
            f"`{render_bar(share, SHARE_BAR_CELLS)}` {share:.0f}% |"
        )
    return rows


def _pipeline_diagram(counts: dict[str, int]) -> list[str]:
    nodes = []
    for index, stage in enumerate(LIFECYCLE_STAGES):
        nodes.append(f'S{index}["{stage_label(stage)} · {counts[stage]}"]')
    return [
        "```mermaid",
        "flowchart LR",
        "    " + " --> ".join(nodes),
        f'    W["Withdrawn · {counts["withdrawn"]}"]',
        "```",
    ]


def _active_lines(statuses: list[dict]) -> list[str]:
    active = [
        data
        for data in sorted(statuses, key=tracker_sort_key)
        if data["stage"] not in {"planned", "published", "withdrawn"}
    ]
    if not active:
        return ["No manuscript is currently beyond the planned stage."]
    lines = []
    for data in active:
        lines.append(
            f"- [{markdown_cell(data['title'])}](./{data['slug']}/) — "
            f"{markdown_cell(data['journal_name'])} · "
            f"{STAGE_ICONS[data['stage']]} {stage_label(data['stage'])} · "
            f"updated {data['updated']}"
        )
    return lines


def _manuscript_rows(statuses: list[dict]) -> list[str]:
    rows = []
    for data in sorted(statuses, key=tracker_sort_key):
        progress = stage_progress(data["stage"])
        if progress is None:
            progress_text = "—"
        else:
            bar = render_bar(progress, PROGRESS_BAR_CELLS)
            progress_text = f"`{bar}` {progress}%"
        rows.append(
            f"| [{markdown_cell(data['title'])}](./{data['slug']}/)<br>"
            f"<sub>{markdown_cell(data['slug'])}</sub> | "
            f"{markdown_cell(data['journal_name'])} | "
            f"{STAGE_ICONS[data['stage']]} {stage_label(data['stage'])} | "
            f"{progress_text} | {data['updated']} |"
        )
    return rows


def render_tracker(statuses: list[dict]) -> str:
    counts = {stage: 0 for stage in STAGES}
    for data in statuses:
        counts[data["stage"]] += 1
    total = len(statuses)
    data_as_of = max(str(data["updated"]) for data in statuses)
    lines = [
        "# Odyssey Manuscript Tracker",
        "",
        "> Visual status for the Odyssey manuscript program. This file is generated from",
        "> each manuscript's `status.json`; update the status record, not this page.",
        "",
        f"**Data as of:** {data_as_of} · **Manuscripts:** {total} · "
        f"**Drafting:** {counts['drafting']} · **Planned:** {counts['planned']} · "
        f"**Published:** {counts['published']}",
        "",
        "## Snapshot",
        "",
        "| Stage | Count | Share |",
        "| --- | ---: | ---: |",
        *_distribution_rows(counts, total),
        "",
        "## Pipeline",
        "",
        *_pipeline_diagram(counts),
        "",
        "## Active work",
        "",
        *_active_lines(statuses),
        "",
        "## All manuscripts",
        "",
        "| Manuscript | Target journal | Stage | Lifecycle position | Updated |",
        "| --- | --- | --- | --- | --- |",
        *_manuscript_rows(statuses),
        "",
        "## Updating this tracker",
        "",
        "1. Change the stage through the manuscript CLI, which updates `status.json`.",
        "2. Regenerate the machine-readable rollup and this visual tracker:",
        "",
        "```bash",
        "python3 manuscripts/tools/manuscripts.py rollup --root manuscripts",
        "python3 manuscripts/tools/manuscripts.py tracker --root manuscripts",
        "```",
        "",
        "Machine-readable data: [rollup.json](./rollup.json).",
        "",
    ]
    return "\n".join(lines)


def cmd_tracker(args: argparse.Namespace) -> None:
    root = Path(args.root)
    statuses = load_all_statuses(root)
    out = Path(args.out) if args.out else root / "TRACKER.md"
    atomic_write_text(out, render_tracker(statuses))
    print(f"tracker: {len(statuses)} manuscripts -> {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Odyssey manuscript sub-repo CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scaffold = sub.add_parser("scaffold")
    p_scaffold.add_argument("slug")
    p_scaffold.add_argument("--root", required=True)
    p_scaffold.add_argument("--seeds", required=True)
    p_scaffold.set_defaults(func=cmd_scaffold)

    p_status = sub.add_parser("status")
    p_status.add_argument("slug")
    p_status.add_argument("stage")
    p_status.add_argument("--root", required=True)
    p_status.add_argument("--note", default=None)
    p_status.set_defaults(func=cmd_status)

    p_rollup = sub.add_parser("rollup")
    p_rollup.add_argument("--root", required=True)
    p_rollup.add_argument("--out", default=None)
    p_rollup.set_defaults(func=cmd_rollup)

    p_tracker = sub.add_parser("tracker")
    p_tracker.add_argument("--root", required=True)
    p_tracker.add_argument("--out", default=None)
    p_tracker.set_defaults(func=cmd_tracker)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
