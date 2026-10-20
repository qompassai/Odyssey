#!/usr/bin/env python3
"""manuscripts.py — Odyssey manuscript sub-repo CLI (slice: scaffold/status/rollup).

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


def fail(message: str) -> "SystemExit":
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(1)


def today() -> str:
    return date.today().isoformat()


def atomic_write_json(path: Path, data: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def cmd_rollup(args: argparse.Namespace) -> None:
    root = Path(args.root)
    entries = []
    for status_path in sorted(root.glob("*/status.json")):
        data = load_status(status_path)
        entries.append(
            {
                "slug": data["slug"],
                "title": data["title"],
                "journal_name": data["journal_name"],
                "stage": data["stage"],
                "updated": data["updated"],
            }
        )
    if not entries:
        fail(f"{root}: no status.json files found")
    rollup = {"generated": today(), "source": "odyssey manuscripts rollup", "manuscripts": entries}
    out = Path(args.out) if args.out else root / "rollup.json"
    atomic_write_json(out, rollup)
    print(f"rollup: {len(entries)} manuscripts -> {out}")


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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
