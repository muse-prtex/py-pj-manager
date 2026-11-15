# AGENTS.md — working with py-pj-manager as an AI agent

py-pj-manager manages a user's Python projects (create / register / open /
git & GitHub). There are three faces over one core:

- **Desktop UI** (`desktop/`, Tauri) — the modern face for humans. It holds
  no logic; it spawns the CLI (below) and renders the JSON.
- **GUI** (`src/pj_manager/app.py`, tkinter) — the zero-dependency fallback
  face for humans. Do not try to automate either GUI.
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
python -m pj_manager.cli init NAME_OR_PATH --json
python -m pj_manager.cli doctor --json
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
- `doctor` checks the environment (Python / venv / git / gh / projects_root
  / data dir / registry / config) and returns `{"ok", "status", "checks",
  "summary"}`. `status` is `ok` / `warn` / `fail`; exit code is 1 only when
  a check fails — warnings (e.g. gh not logged in, a registered folder
  gone) keep exit 0. Run it first when something looks off; the desktop
  UI runs it at startup and shows the result in the sidebar.

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
  names). Names are unique in the registry: registering or creating a
  second project with an already-used name is rejected, because commands
  address projects by name. A corrupt `projects.json` is backed up to
  `projects.json.bak-<日時>` before the next save overwrites it; malformed
  entries are skipped (and reported by `doctor`) instead of crashing
  other commands.

## Developing

- The Python core is standard library only — no new dependencies there.
  (The optional Tauri shell in `desktop/` is Rust and holds no logic.)
- Logic goes in `src/pj_manager/core.py` (GUI-free, unit-tested); the GUI in
  `app.py`; the CLI in `cli.py`.
- Tests: `python -m unittest discover -s tests -v` (also standard library
  only). Add tests when you change `core.py` or `cli.py`.
- The GUI targets Windows; `core.py` and `cli.py` must stay importable and
  testable on any platform.
