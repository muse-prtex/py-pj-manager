# AGENTS.md — working with py-pj-manager as an AI agent

py-pj-manager manages a user's Python projects (create / register / open /
git & GitHub). There are three faces over one core:

- **Desktop UI** (`desktop/`, Tauri) — the modern face for humans. It holds
  no logic; it spawns the CLI (below) and renders the JSON.
- **GUI** (`src/pj_manager/app.py`, tkinter) — the zero-dependency fallback
  face for humans. Do not try to automate either GUI. Keyboard shortcuts:
  `Ctrl+N` new, `Ctrl+O` register, `F5` / `Ctrl+R` refresh, `Enter` open
  the selected project in a terminal, `Delete` unregister, `Ctrl+Q` quit.
- **CLI** (`src/pj_manager/cli.py`) — for scripts and AI agents. Use this.

## The CLI

Run from the repository root (or anywhere, with `PYTHONPATH=<repo>/src`),
or install it once (`pip install -e .` from the repo root, see
`pyproject.toml`) and call it as `pj-manager` — same contract, no
`PYTHONPATH` needed:

```
pj-manager list --json
pj-manager create my-app [--root DIR] [--no-venv] [--no-git] [--github none|private|public] --json
python -m pj_manager.cli register PATH --json
python -m pj_manager.cli unregister NAME --json
python -m pj_manager.cli status NAME_OR_PATH --json
python -m pj_manager.cli commit NAME_OR_PATH -m "message" --json
python -m pj_manager.cli push NAME_OR_PATH --json
python -m pj_manager.cli pull NAME_OR_PATH --json
python -m pj_manager.cli log NAME_OR_PATH [-n N] --json
python -m pj_manager.cli init NAME_OR_PATH --json
python -m pj_manager.cli doctor --json
python -m pj_manager.cli check --json
python -m pj_manager.cli config show --json
python -m pj_manager.cli config set-root DIR --json
python -m pj_manager.cli config set-language ja|en --json
```

Display language: `config.json` `language` ("ja" default / "en"). The CLI's
human-readable output, the tkinter GUI and the desktop UI follow it;
`--json` output does not change with the language.
UI strings live in `src/pj_manager/i18n.py` (`STRINGS`); add a key there and
use `i18n.t(key, …)` instead of writing a user-facing string inline. New
projects' `README.md` template is still Japanese.


Contract:

- `--json` may appear in any position. With it, stdout is exactly one JSON
  object: `{"ok": true, ...}` on success, `{"ok": false, "error": "..."}`
  on failure.
- Exit code is 0 on success, 1 on failure. argparse usage errors exit 2.
- Nothing is interactive. `commit` requires `-m`. Committing a clean
  tree succeeds (exit 0) with a localized "nothing to commit" message
  instead of failing — the desired end state is already met; a real
  failure (hook rejection, missing git identity) still exits 1.
  When git user.name / user.email is not set, `commit` fails (exit 1)
  with a friendly, localized message that gives the two
  `git config --global` commands, instead of git's raw "Author
  identity unknown" — detected by `core.git_identity_configured()`
  (`git config user.name` / `user.email` exit codes, plus the
  GIT_AUTHOR_* / GIT_COMMITTER_* fallbacks git honors). A clean tree
  still commits successfully with no identity set.
- An empty commit message (`-m ""` or whitespace only) fails (exit 1)
  with a friendly, localized message — "コミットメッセージが空です
  （-m \"メッセージ\" でコミットメッセージを指定してください）" /
  "Commit message is empty (specify one with -m \"message\")" — instead
  of git's raw "Aborting commit due to empty commit message." The check
  runs in `core.commit_all` before `git add -A`, so nothing gets
  staged, and before the clean-tree check, so it also fails on a clean
  tree. Both GUIs already guard this on their side (tkinter returns
  early on an empty dialog answer; the desktop UI shows its inline
  error), so the core check covers the CLI and agent callers.
- `status` output includes `git` (branch / dirty count / ahead / behind /
  last_commit) and `has_venv` — use it instead of shelling out to git for a
  quick health check. `status` fails (exit 1, `{"ok": false, "error": ...}`)
  when the registered folder is gone — a missing folder is not "not a git
  repository". `list` marks such a row `[missing]` in human output; the
  JSON still carries `exists: false`. `log` on a repository with no
  commits yet succeeds with an empty list (`{"ok": true, "log": []}`) and
  a localized "no commits yet" message instead of failing with git's raw
  "does not have any commits yet" — an empty history is not a failure.
  `log -n` with a count of 0 or a negative number fails (exit 1) with a
  friendly, localized message — "表示件数には1以上の整数を指定して
  ください（-n N）" / "Number of commits must be a positive integer
  (use -n N)" — instead of passing "-0" / "--1" to `git log` and
  returning git's raw "fatal: unrecognized argument: --1". The check
  runs in `cli.cmd_log` before git and before the empty-repo success
  path. A positive count still lists that many commits.
- `push` / `pull` with no remote or no upstream branch configured still
  fail (exit 1) — the desired end state is not met — but with a
  friendly, localized message that says what to do next
  ("リモートが設定されていません…" / "No remote is configured …",
  "上流ブランチが設定されていません…" / "No upstream branch is
  configured …") instead of git's raw English output. A real failure
  (an unreachable remote, an authentication error) still passes git's
  output through unchanged, and a repository with no commits yet keeps
  git's own message. The tkinter GUI's push / pull buttons use the same
  path (`core.git_push_pull`), so they show the friendly message too.
- `doctor` checks the environment (Python / venv / git / gh / git
  identity / projects_root / data dir / registry / config) and returns
  `{"ok", "status", "checks", "summary"}`. The `git_identity` check
  looks at the *global* user.name / user.email and warns when they
  are not set (per-repository identity still works for commits, and
  the hint says so). `status` is `ok` / `warn` / `fail`; exit code is 1 only when
  a check fails — warnings (e.g. gh not logged in, a registered folder
  gone) keep exit 0. Run it first when something looks off; the desktop
  UI runs it at startup and shows the result in the sidebar.
- `check` reports the health of *every* registered project in one JSON
  object: `{"ok", "projects", "summary"}`. Each project carries `state`
  (`ok` / `attention` / `missing`), `has_venv`, the `git` numbers
  (branch / dirty / ahead / behind / last_commit) and an `issues` list
  of short tags (`dirty:2`, `ahead:1`, `behind:1`, `no-venv`, `not-git`,
  `missing`). The overall `ok` is false only when a registered folder
  is gone (exit code 1); dirty / ahead / behind / no-venv are
  `attention`, not failure. Use it instead of looping `status` over
  every project.

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
