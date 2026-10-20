#!/usr/bin/env python3
"""test_manuscripts.py — unit tests for the Odyssey manuscripts CLI slice.

Coverage map (validation + adversarial, roughly half and half):

  * stage-enum validation: every STAGES value accepted by load_status;
    invalid, empty, and case-variant stages rejected; the CLI `status`
    command refuses an invalid stage and leaves status.json untouched.
  * status.json schema: missing required key, malformed JSON, and a
    non-list history are all hard errors (fail closed, SystemExit 1).
  * rollup: the real staging tree yields exactly 11 entries in
    deterministic slug order with fields matching the status files;
    two runs are byte-identical; a malformed status.json anywhere in
    the tree aborts the rollup and writes no output (fail loudly,
    never silently skip); an empty root is refused.
  * tracker: the generated Markdown visualizes all 11 manuscripts,
    stage counts, the pipeline, and lifecycle progress in a
    deterministic order; malformed input writes nothing; punctuation
    in titles and journal names cannot break the Markdown table;
    withdrawn manuscripts do not receive a lifecycle percentage.
  * scaffold: creates the layout with stage=planned and never clobbers
    an existing status.json on re-run; an unknown slug is refused.
  * check/package gate: this CLI slice deliberately ships no check or
    package command (see the manuscripts.py module docstring — they
    land with the journal-profile step). Packaging is therefore refused
    at the CLI boundary, unconditionally: invoking `check` or
    `package` exits nonzero. A fortiori, packaging cannot proceed
    when a check would fail.
  * approval-stamp voiding: this slice likewise ships no `submit`
    command (it lands with the Playwright step). No status.json stamp
    can be honored by this CLI: `submit` exits nonzero both with a
    fresh `approved` stamp and after the submission/ package changes
    (the stamp-voiding case) — submission cannot proceed either way.

Run:  python3 -m unittest test_manuscripts -v     (from this directory)
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
STAGE_ROOT = TOOLS_DIR.parent
SEEDS_PATH = TOOLS_DIR / "seeds.json"
CLI_PATH = TOOLS_DIR / "manuscripts.py"

sys.path.insert(0, str(TOOLS_DIR))
import manuscripts as ms  # noqa: E402


def valid_status(**overrides):
    """A minimal schema-valid status.json payload, with overrides."""
    data = {
        "slug": "pilot-x",
        "title": "Pilot Title",
        "journal_name": "Pilot Journal",
        "profile_key": "pilot",
        "stage": "planned",
        "updated": "2026-10-19",
        "history": [{"date": "2026-10-19", "event": "seeded"}],
    }
    data.update(overrides)
    return data


def run_cli(*argv):
    """Run manuscripts.py as a subprocess; return the CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *argv],
        capture_output=True,
        text=True,
        timeout=60,
    )


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="manuscripts-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write_status(self, root, slug, payload):
        target = Path(root) / slug
        target.mkdir(parents=True, exist_ok=True)
        path = target / "status.json"
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path


class StageEnumValidationTests(TempDirCase):
    def test_every_valid_stage_accepted(self):
        for stage in ms.STAGES:
            with self.subTest(stage=stage):
                path = self.write_status(self.tmp, "pilot-x", valid_status(stage=stage))
                data = ms.load_status(path)
                self.assertEqual(data["stage"], stage)

    def test_invalid_stage_rejected(self):
        path = self.write_status(self.tmp, "pilot-x", valid_status(stage="in-review-typo"))
        with self.assertRaises(SystemExit) as ctx:
            ms.load_status(path)
        self.assertEqual(ctx.exception.code, 1)

    def test_empty_stage_rejected(self):
        path = self.write_status(self.tmp, "pilot-x", valid_status(stage=""))
        with self.assertRaises(SystemExit):
            ms.load_status(path)

    def test_case_variant_stage_rejected(self):
        # The enum is exact-match: "Drafting" is not "drafting".
        path = self.write_status(self.tmp, "pilot-x", valid_status(stage="Drafting"))
        with self.assertRaises(SystemExit):
            ms.load_status(path)


class StatusSchemaTests(TempDirCase):
    def test_missing_required_key_rejected(self):
        payload = valid_status()
        del payload["title"]
        path = self.write_status(self.tmp, "pilot-x", payload)
        with self.assertRaises(SystemExit):
            ms.load_status(path)

    def test_malformed_json_rejected(self):
        path = self.write_status(self.tmp, "pilot-x", "{not json")
        with self.assertRaises(SystemExit):
            ms.load_status(path)

    def test_history_must_be_a_list(self):
        path = self.write_status(self.tmp, "pilot-x", valid_status(history={"date": "x"}))
        with self.assertRaises(SystemExit):
            ms.load_status(path)


class CliStatusCommandTests(TempDirCase):
    def scaffold_pilot(self, slug="resident-local-models"):
        result = run_cli("scaffold", slug, "--root", str(self.tmp), "--seeds", str(SEEDS_PATH))
        self.assertEqual(result.returncode, 0, result.stderr)
        return self.tmp / slug / "status.json"

    def test_cli_status_valid_stage_updates_and_appends_history(self):
        status_path = self.scaffold_pilot()
        result = run_cli(
            "status", "resident-local-models", "drafting",
            "--root", str(self.tmp), "--note", "Drafting began",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(status_path.read_text(encoding="utf-8"))
        self.assertEqual(data["stage"], "drafting")
        self.assertEqual(data["history"][-1]["event"], "Drafting began")

    def test_cli_status_invalid_stage_refused_and_file_untouched(self):
        status_path = self.scaffold_pilot()
        before = status_path.read_bytes()
        result = run_cli(
            "status", "resident-local-models", "almost-there", "--root", str(self.tmp),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not in the stage enum", result.stderr)
        self.assertEqual(status_path.read_bytes(), before)

    def test_cli_status_missing_manuscript_refused(self):
        result = run_cli("status", "no-such-slug", "drafting", "--root", str(self.tmp))
        self.assertEqual(result.returncode, 1)


class ScaffoldTests(TempDirCase):
    def test_scaffold_creates_layout_at_planned(self):
        result = run_cli(
            "scaffold", "kintsugi-clinical-battery",
            "--root", str(self.tmp), "--seeds", str(SEEDS_PATH),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        target = self.tmp / "kintsugi-clinical-battery"
        for sub in ("manuscript", "figures", "submission"):
            self.assertTrue((target / sub / ".gitkeep").exists(), sub)
        self.assertTrue((target / "refs.bib").exists())
        self.assertTrue((target / "NOTES.md").exists())
        data = json.loads((target / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(data["stage"], "planned")
        self.assertEqual(data["journal_name"], "JAMIA")

    def test_scaffold_never_clobbers_existing_status(self):
        run_cli("scaffold", "resident-local-models", "--root", str(self.tmp),
                "--seeds", str(SEEDS_PATH))
        run_cli("status", "resident-local-models", "drafting", "--root", str(self.tmp))
        result = run_cli("scaffold", "resident-local-models", "--root", str(self.tmp),
                         "--seeds", str(SEEDS_PATH))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(
            (self.tmp / "resident-local-models" / "status.json").read_text(encoding="utf-8")
        )
        self.assertEqual(data["stage"], "drafting")

    def test_scaffold_unknown_slug_refused(self):
        result = run_cli("scaffold", "not-a-real-slug", "--root", str(self.tmp),
                         "--seeds", str(SEEDS_PATH))
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.tmp / "not-a-real-slug").exists())


class RollupTests(TempDirCase):
    def test_rollup_real_tree_eleven_entries_sorted_and_sourced(self):
        out = self.tmp / "rollup-out.json"
        result = run_cli("rollup", "--root", str(STAGE_ROOT), "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(out.read_text(encoding="utf-8"))
        entries = data["manuscripts"]
        self.assertEqual(len(entries), 11)
        slugs = [e["slug"] for e in entries]
        self.assertEqual(slugs, sorted(slugs))  # deterministic order
        seeds = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(slugs), set(seeds.keys()))
        for entry in entries:
            self.assertEqual(entry["title"], seeds[entry["slug"]]["title"])
            self.assertEqual(entry["journal_name"], seeds[entry["slug"]]["journal_name"])
            self.assertIn(entry["stage"], ms.STAGES)
        by_slug = {e["slug"]: e for e in entries}
        self.assertEqual(by_slug["viewpoint-nature-medicine"]["stage"], "drafting")
        others = [s for s in slugs if s != "viewpoint-nature-medicine"]
        for slug in others:
            self.assertEqual(by_slug[slug]["stage"], "planned", slug)

    def test_rollup_output_is_deterministic(self):
        out_a, out_b = self.tmp / "a.json", self.tmp / "b.json"
        self.assertEqual(
            run_cli("rollup", "--root", str(STAGE_ROOT), "--out", str(out_a)).returncode, 0)
        self.assertEqual(
            run_cli("rollup", "--root", str(STAGE_ROOT), "--out", str(out_b)).returncode, 0)
        self.assertEqual(out_a.read_bytes(), out_b.read_bytes())

    def test_rollup_fails_closed_on_one_malformed_status(self):
        # One good manuscript, one with an out-of-enum stage: the whole
        # rollup must abort and write nothing (never silently skip).
        self.write_status(self.tmp, "good-one", valid_status(slug="good-one"))
        self.write_status(self.tmp, "bad-one", valid_status(slug="bad-one", stage="bogus"))
        out = self.tmp / "rollup.json"
        result = run_cli("rollup", "--root", str(self.tmp), "--out", str(out))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())

    def test_rollup_empty_root_refused(self):
        result = run_cli("rollup", "--root", str(self.tmp), "--out", str(self.tmp / "r.json"))
        self.assertEqual(result.returncode, 1)


class TrackerTests(TempDirCase):
    def test_tracker_real_tree_visualizes_all_manuscripts(self):
        out = self.tmp / "TRACKER.md"
        result = run_cli("tracker", "--root", str(STAGE_ROOT), "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text(encoding="utf-8")
        self.assertIn("# Odyssey Manuscript Tracker", text)
        self.assertIn("**Data as of:** 2026-10-19", text)
        self.assertIn("**Manuscripts:** 11", text)
        self.assertIn("```mermaid", text)
        self.assertIn('S0["Planned · 10"]', text)
        self.assertIn('S1["Drafting · 1"]', text)
        for seed in json.loads(SEEDS_PATH.read_text(encoding="utf-8")).values():
            self.assertIn(seed["title"], text)
            self.assertIn(seed["journal_name"], text)
        self.assertLess(
            text.index("viewpoint-nature-medicine"),
            text.index("ai-tutors-med-ed"),
        )

    def test_tracker_default_output_and_determinism(self):
        self.write_status(self.tmp, "pilot-x", valid_status())
        first = run_cli("tracker", "--root", str(self.tmp))
        self.assertEqual(first.returncode, 0, first.stderr)
        out = self.tmp / "TRACKER.md"
        first_bytes = out.read_bytes()
        second = run_cli("tracker", "--root", str(self.tmp))
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(out.read_bytes(), first_bytes)

    def test_tracker_fails_closed_on_malformed_status(self):
        self.write_status(self.tmp, "good-one", valid_status(slug="good-one"))
        self.write_status(self.tmp, "bad-one", valid_status(slug="bad-one", stage="bogus"))
        out = self.tmp / "TRACKER.md"
        result = run_cli("tracker", "--root", str(self.tmp), "--out", str(out))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())

    def test_tracker_empty_root_refused(self):
        out = self.tmp / "TRACKER.md"
        result = run_cli("tracker", "--root", str(self.tmp), "--out", str(out))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(out.exists())

    def test_tracker_escapes_table_breaking_text(self):
        status = valid_status(
            title="A | B [Draft]",
            journal_name="Journal | One",
        )
        text = ms.render_tracker([status])
        self.assertIn("A \\| B \\[Draft\\]", text)
        self.assertIn("Journal \\| One", text)

    def test_tracker_withdrawn_has_no_lifecycle_percentage(self):
        text = ms.render_tracker([valid_status(stage="withdrawn")])
        self.assertIn("⛔ Withdrawn", text)
        self.assertIn("| — |", text)
        self.assertNotIn("100%", text.split("## All manuscripts", 1)[1])


class CheckPackageGateTests(TempDirCase):
    """check/package are out of this slice by contract (module docstring):
    the commands do not exist, so packaging is refused at the CLI
    boundary — it cannot proceed under any input, passing check or not."""

    def test_check_command_refused(self):
        result = run_cli("check", "resident-local-models", "--root", str(self.tmp))
        self.assertNotEqual(result.returncode, 0)

    def test_package_command_refused(self):
        result = run_cli("package", "resident-local-models", "--root", str(self.tmp))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.tmp / "resident-local-models" / "submission" / "portal-fields.json").exists())


class ApprovalStampTests(TempDirCase):
    """submit is out of this slice by contract: no `approved` stamp can
    be honored by this CLI, stamped or voided — submit always refuses."""

    def _stamped_manuscript(self):
        run_cli("scaffold", "resident-local-models", "--root", str(self.tmp),
                "--seeds", str(SEEDS_PATH))
        target = self.tmp / "resident-local-models"
        status_path = target / "status.json"
        data = json.loads(status_path.read_text(encoding="utf-8"))
        data["stage"] = "packaged"
        data["approved"] = {"by": "Matt", "package_sha256": "deadbeef"}
        status_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        package_file = target / "submission" / "manuscript.pdf"
        package_file.write_bytes(b"%PDF-fake-package-v1")
        return target, package_file

    def test_submit_refused_even_with_approval_stamp(self):
        self._stamped_manuscript()
        result = run_cli("submit", "resident-local-models", "--root", str(self.tmp))
        self.assertNotEqual(result.returncode, 0)

    def test_submit_refused_after_package_changes_post_stamp(self):
        _target, package_file = self._stamped_manuscript()
        # The package changes after stamping: under the program rules
        # this voids the stamp. This CLI cannot submit either way.
        package_file.write_bytes(b"%PDF-fake-package-v2-CHANGED")
        result = run_cli("submit", "resident-local-models", "--root", str(self.tmp))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
