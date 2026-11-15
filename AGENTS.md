# AGENTS.md — working with py-pj-manager as an AI agent

py-pj-manager manages a user's Python projects (create / register / open /
git & GitHub). There are two faces over one core:

- **GUI** (`src/pj_manager/app.py`, tkinter) — for humans. Do not try to
  automate the GUI.
- **CLI** (`src/pj_manager/cli.py`) — for scripts and AI agents. Use this.

## The CLI

Run from the repository root (or anywhere, with `PYTHONPATH=<repo>/src`):

```
python -m pj_manager.cli list --json
python -m pj_manager.cli create my-app [--root DIR] [--no-venv] [--no-git] [--github none|private|public] --json
python -m pj_manager.cli register PATH --json
python -m pj_manager.cli unregister NAME --json
python -m pj_manager.cli status NAME_OR_PATH --json
python -m pj_manager.cli commit NAME_OR_PATH -m "message" --json
python -m pj_manager.cli push NAME_OR_PATH --json
python -m pj_manager.cli pull NAME_OR_PATH --json
python -m pj_manager.cli log NAME_OR_PATH [-n N] --json
python -m pj_manager.cli config show --json
python -m pj_manager.cli config set-root DIR --json
```

Contract:

- `--json` may appear in any position. With it, stdout is exactly one JSON
  object: `{"ok": true, ...}` on success, `{"ok": false, "error": "..."}`
  on failure.
- Exit code is 0 on success, 1 on failure. argparse usage errors exit 2.
- Nothing is interactive. `commit` requires `-m`.
- `status` output includes `git` (branch / dirty count / ahead / behind /
  last_commit) and `has_venv` — use it instead of shelling out to git for a
  quick health check.

## State and safety

- State lives in `projects.json` and `config.json` in the repository root.
  The `PJ_MANAGER_DATA_DIR` environment variable redirects both files —
  always use it to point at a sandbox when testing, so you never touch the
  user's real registry.
- **Never edit `projects.json` directly**; go through the CLI so validation
  and sorting stay consistent.
- **Unregistering never deletes a project folder.** Nothing in this tool
  deletes project folders — keep it that way.
- Project names must match `^[A-Za-z0-9][A-Za-z0-9_-]*$` (they become folder
  names).

## Developing

- Standard library only. No new dependencies.
- Logic goes in `src/pj_manager/core.py` (GUI-free, unit-tested); the GUI in
  `app.py`; the CLI in `cli.py`.
- Tests: `python -m unittest discover -s tests -v` (also standard library
  only). Add tests when you change `core.py` or `cli.py`.
- The GUI targets Windows; `core.py` and `cli.py` must stay importable and
  testable on any platform.
