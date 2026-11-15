# Changelog

## 0.6.0 — 2026-11-16

- CLI: added the `doctor` command — checks Python / venv / git / gh /
  projects_root / data dir / registry / config and returns the health
  as `--json` (`ok` / `status` / `checks` / `summary`; exit 1 only on
  `fail`, warnings keep exit 0). Missing project folders and a corrupt
  registry are reported instead of crashing other commands.
- Desktop UI: runs `doctor` at startup and shows the result in the
  sidebar (`環境チェック: warn (7 ok / 1 warn / 0 fail)`); non-ok
  checks are also written to the log panel. No Rust change needed —
  the shell already forwards any CLI command as JSON.

## 0.5.0 — 2026-11-16

- Added a modern desktop UI in `desktop/` (Tauri: Rust shell + web
  frontend). The shell holds no logic — it drives the Python core through
  the CLI (`--json`), so desktop / tkinter GUI / agents share one core.
- CLI: added the `init` command (git init for a registered project).
- The tkinter GUI remains as the zero-dependency fallback face.

## 0.4.0 — 2026-11-16

- GUI redesign: dark sidebar + white cards + accent blue, flat modern look
  (ttk "clam" theme, Yu Gothic UI on Windows). Same layout and behaviour,
  no functional changes.

## 0.3.0 — 2026-11-16

- Added an automation CLI (`src/pj_manager/cli.py`): list / create / register /
  unregister / status / commit / push / pull / log / config, with a `--json`
  contract (single JSON object, exit 0/1, no prompts) designed for scripts
  and AI agents. See AGENTS.md.
- `PJ_MANAGER_DATA_DIR` environment variable can redirect the data files
  (projects.json / config.json), e.g. to a sandbox for testing.
- Fixed: saving the registry/config failed when the data folder did not
  exist yet (found by exercising the new CLI against a fresh sandbox).
- Added AGENTS.md (how agents should drive this tool) and CLI tests
  (10 tests total, all passing).

## 0.2.0 — 2026-11-16

- Restructured into a `src/` package layout (`src/pj_manager/`) so the
  project can grow without a major reorganization later. `run.bat` and the
  root `pjman.py` shim keep the old launch habits working; data files
  (`projects.json` / `config.json`) still live in the repository root.
- Added a `unittest` suite for the core logic (`tests/`) and a GitHub
  Actions workflow (Windows + Ubuntu).
- Added issue templates.

## 0.1.0 — 2026-11-16

Initial open-source release.

- Project list with venv / git status at a glance
- One-go project creation: scaffold + template + `.venv` + `git init` +
  initial commit + optional GitHub repository
- Register existing project folders
- Open in a venv-activated terminal, VS Code, or Explorer
- Git operations: commit, push, pull, log, init
- GitHub operations via the `gh` CLI
- Standard library only; runs by double-clicking `run.bat`
