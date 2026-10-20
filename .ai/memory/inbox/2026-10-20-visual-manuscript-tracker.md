# Visual manuscript tracker

Implemented 2026-10-20.

- `manuscripts/TRACKER.md` is the generated visual tracker for the Odyssey
  manuscript program.
- Each manuscript's `status.json` remains the single source of truth.
- `manuscripts/tools/manuscripts.py tracker --root manuscripts` regenerates
  the tracker after status changes.
- `manuscripts/rollup.json` remains the machine-readable aggregate.
- The generator and tracker are covered by the manuscripts CLI test suite
  (27 tests passing at implementation time).
