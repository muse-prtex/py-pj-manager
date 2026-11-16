# Changelog

## 0.14.0 — 2026-11-16

- New-project dialog now opens centered over the main window. It used
  to set a bare `geometry("460x380")` and leave placement to the window
  manager, which put it offset to the top-left of the main window
  (spotted in the session 11 screenshot). A pure `center_geometry()`
  helper computes the centered position and clamps it inside the screen
  (parent near a screen edge, or a dialog larger than the screen, can no
  longer push it off-screen); `App._center_dialog()` applies it from the
  live parent/screen sizes.
- Real use: opened the GUI on Xvfb with the sandbox registry and pressed
  `Ctrl+N` — the dialog opened centered over the main window
  (screenshot `session12-dialog-centered.png`, geometry verified
  numerically). The main window itself is unchanged.
- Tests: 9 new tests in `tests/test_dialogs.py` (centered position,
  screen-edge clamping, dialog larger than the screen, wiring of
  `dialog_new` / `_center_dialog`). 94 tests total, all passing.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed with
  the GitHub connector — `push_files` / `create_or_update_file` accept
  UTF-8 text only (the connector guide and the live tool catalogue were
  re-checked this session: `create_or_update_file` takes a string which
  the server base64-encodes, so raw PNG bytes have no route through it).
  The images are in Box as `docs-images-v0.12.0.zip` (`12_Muse/PJマネージャー`);
  adding them via the GitHub web UI to `docs/images/` fixes the links in
  `docs/usage.md` and the READMEs.

## 0.13.0 — 2026-11-16

- Keyboard shortcuts in the tkinter GUI (reserve-improvement slot):
  `Ctrl+N` new project, `Ctrl+O` register an existing folder, `F5` /
  `Ctrl+R` refresh the list and detail, `Enter` open the selected
  project in a venv-activated terminal, `Delete` unregister the selected
  project, `Ctrl+Q` quit. The shortcuts are listed in a hint line at
  the bottom-left of the sidebar (Japanese / English, follows the
  language setting). List-only keys (`Enter` / `Delete`) are bound to
  the project list itself, so pressing `Delete` while typing in a field
  cannot trigger an unregister dialog. Bindings are re-applied on every
  rebuild (language switch destroys and recreates the widgets).
- Real use: opened the GUI on Xvfb with the sandbox registry and
  pressed `Ctrl+N` — the new-project dialog actually opened
  (screenshot `session11-shortcut-new.png`). `F5` / `Ctrl+R` use the
  same binding path (`_bind_shortcuts`, covered by tests). Screenshots
  in `docs/images/` are unchanged (the GUI layout is the same apart
  from the hint line).
- Tests: 9 new tests in `tests/test_shortcuts.py` (shortcut table,
  handler existence, no duplicate key per scope, hint in both
  languages naming every shortcut, `_build` rebinds). 85 tests total,
  all passing.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed
  with the GitHub connector — `push_files` / `create_or_update_file`
  accept UTF-8 text only (the server base64-encodes the string it is
  given, so binary content has no route through it; confirmed against
  the live tool catalogue this session). Session 11 also tried the
  GitHub web UI, but the browser has no saved GitHub login and no
  login flow is started, so the upload was blocked at sign-in. The
  images are handed to the user as a ready-to-upload ZIP via Box
  (`12_Muse/PJマネージャー/docs-images-v0.12.0.zip`) instead — drag
  the 7 PNGs into `docs/images/` on the GitHub web UI and the links
  in `docs/usage.md` and the READMEs will resolve.

## 0.12.0 — 2026-11-16

- Documentation: new `docs/usage.md` — a full usage guide with real
  screenshots (GUI, desktop app incl. empty state and new-project modal,
  English GUI, `doctor` / `check` runs). The screenshots live in
  `docs/images/` and are real captures taken while using the tool, not
  mock-ups. README.md and README.ja.md now show the GUI and desktop
  screenshots near the top and link to the guide.
- Real use: every command and output quoted in the guide was actually run
  in a sandbox first (`create` with venv + git init + initial commit,
  `register` of a plain folder, `list` / `status` / `doctor` / `check`) —
  the quoted outputs are verbatim from those runs, including the
  `gh not logged in` warning in `doctor` and the `attention` state of a
  non-git project in `check`. The GUI screenshot is a fresh capture of
  v0.12.0 under Xvfb; the desktop and CLI shots are reused from the
  sessions that verified those screens (v0.8.0 desktop UI, v0.10.0
  `check`, v0.11.0 English GUI) — the UIs have not changed since.
- Tests: 9 new tests in `tests/test_docs.py` (every image referenced from
  usage.md / README.md / README.ja.md exists and is a real PNG, every
  file in `docs/images/` is referenced, required sections exist, links
  resolve inside the repo, no `sandbox://` paths leak into the docs).
  76 tests total, all passing.

## 0.11.0 — 2026-11-16

- Language switch groundwork: all UI strings now live in one dictionary
  (`src/pj_manager/i18n.py`, `STRINGS`, ja/en). The display language is
  `config.json` `language` ("ja" default / "en"), switched from the
  **言語 / Language** dropdown at the bottom-left of the tkinter GUI or
  with `pj-manager config set-language ja|en` (unknown values are
  rejected, and the previous language stays). The CLI's human-readable
  output (doctor details, error messages, status/check lines) and the
  whole tkinter GUI follow the setting; `--json` output (keys and values)
  does not change with the language. `i18n.check_dictionaries()` and a
  test that every key referenced from core.py / cli.py / app.py exists
  guard the dictionaries; `load_config()` normalizes an unknown language
  back to "ja".
- Real use: created a project with venv + git init + initial commit and
  registered a plain folder in a sandbox, then ran list / status /
  doctor / check in both languages. English doctor details and error
  messages ("Not a git repository: … (run `init` first …)", "Project not
  found: …") were verified, as was switching back to Japanese. The GUI
  was opened under Xvfb in both languages (screenshots) and the language
  was switched from inside the GUI — the switcher saves the setting and
  rebuilds the window. Caught by the real run: switching languages used
  to drop the selected project (the detail fell back to the placeholder);
  `_rebuild()` now keeps the selection and re-shows the detail.
  A `gui_shot.py` quirk was also found and fixed in the tool: with the
  default `event_generate` the language event is processed synchronously
  and the selection event queued right after it is lost to the rebuild,
  so the tool now queues the switch with `when="tail"` and selects after
  a short delay (real clicks go through the mainloop, so this never
  affects actual use).
- Not yet switched: the strings in the Tauri desktop UI
  (`desktop/ui/index.html`) are still Japanese-only; they follow in a
  later session. The README template written into a newly created project
  is also still Japanese for now.
- Tests: 12 new tests in `tests/test_i18n.py` (dictionary completeness,
  referenced-key coverage, language normalization, core messages and
  doctor details in both languages, CLI `set-language` incl. rejection
  of unknown values, `--json` being language-independent). 67 tests
  total, all passing.

## 0.10.0 — 2026-11-16

- Cross-project health check: new `check` command (`core.check_all()` +
  `cli.py`). One JSON object covers every registered project: `state`
  (`ok` / `attention` / `missing`), `has_venv`, the `git` numbers
  (branch / dirty / ahead / behind / last_commit) and a short `issues`
  tag list (`dirty:2`, `ahead:1`, `behind:1`, `no-venv`, `not-git`,
  `missing`), plus a `summary` of counts. Overall `ok` is false (exit
  code 1) only when a registered folder is gone; dirty / ahead / behind
  / no-venv are `attention`, not failure — the same thinking as
  `doctor`. Human output is one line per project plus a summary line.
- Real use: six projects in a sandbox with deliberately different
  states (clean + venv, dirty, ahead of a bare remote, behind a bare
  remote, not a git repo, folder deleted after registering) — `check`
  reported all six states and counts correctly, exit code 1 only for
  the missing folder. Caught by the real run: nothing broke, but the
  test setup itself needed the same care as the feature (bare-remote
  HEAD must point at `main`, and `behind` only shows with an upstream
  set) — both are now pinned by tests.
- Tests: 11 new tests in `tests/test_check.py` (core states incl.
  ahead/behind against a bare remote, mixed summary counts, CLI JSON +
  human output, exit codes). 55 tests total, all passing.

## 0.9.0 — 2026-11-16

- Packaging: added `pyproject.toml`, so the tool installs with
  `pip install -e .` (or `pip install .`) and provides the `pj-manager`
  console script — no `PYTHONPATH` juggling needed. The Python core
  stays standard-library only (`dependencies = []`, `requires-python
  >= 3.10`); the version is read from `pj_manager.__version__`
  (single source of truth). `run.bat` / `py pjman.py` still work
  without installing.
- Real use: installed into a fresh venv and actually used the
  `pj-manager` command (create with venv + git init + initial commit,
  status, doctor, list). A plain `pip install .` into a second venv
  was also verified — the package lands in site-packages and reads
  the same registry. Caught by the real install: the first draft
  forgot `dynamic = ["version"]` in `[project]`, which setuptools
  rejects; fixed, and a test now pins that declaration.
- Tests: 7 new tests in `tests/test_pyproject.py` (metadata: build
  system, name, zero dependencies, version wiring, console-script
  entry point, src layout; plus entry-point runs as a subprocess).
  44 tests total, all passing.

## 0.8.0 — 2026-11-16

- Desktop UI polish (verified by actually opening the modals and the empty
  state in a browser and screenshotting them):
  - Zero-project empty state: the detail / open / Git cards are hidden and
    a hero card is shown instead ("まだプロジェクトがありません" with
    新規作成 / 既存フォルダを登録 buttons that work). Before, the main
    area showed a bare "プロジェクトを選んでください" with dead buttons.
    Demo preview: open the page with `?demo=empty`.
  - Modals can now be closed with Esc or by clicking the overlay, not
    only the キャンセル button.
  - Inline validation instead of `alert()`: an invalid project name
    ("bad name!") now shows "使えるのは半角英数字・-・_ で、先頭は英数字
    にしてください" under the field and keeps the modal open; the commit
    modal shows which project it commits ("コミット — alpha-tool") and
    reports an empty message inline.
- New tool: `day-run/tools/desktop_shot.py` — screenshots the desktop UI
  in demo mode (normal view, new-project modal, name error, commit modal,
  empty state) with Playwright + the bundled Chrome, and asserts the
  modals really open and Esc closes them.
- Tests: 6 new static checks for the desktop UI
  (`tests/test_desktop_ui.py`, incl. a `node --check` of the inline
  script when node is available). 37 tests total, all passing.

## 0.7.0 — 2026-11-16

- Robustness (found by actually exercising the CLI on boundary cases):
  - Project names are now unique in the registry: registering a second
    folder with an already-used name, or creating a project with a
    registered name, is rejected with a clear error. Before, two
    entries could share a name and `unregister` would remove both.
  - A corrupt `projects.json` is no longer silently overwritten: the
    next save first backs it up to `projects.json.bak-<日時>`.
  - Malformed registry entries (not a dict, or missing `name`/`path`)
    no longer crash `list` / `register` with `KeyError`; they are
    skipped, and `doctor` reports them as a warning.
  - `doctor` also warns about duplicate names in the registry, and
    treats an empty (0-byte) `projects.json` / `config.json` as an
    empty registry / defaults instead of reporting it corrupt.
  - `commit` / `log` / `push` / `pull` on a non-git folder now say
    `git リポジトリではありません（先に init してください）` instead of
    passing git's raw `fatal:` through; on a deleted (ghost) folder
    they say `フォルダがありません` instead of the misleading
    `コマンドが見つかりません: git`.
  - Over-long project names (over 255 bytes) are rejected with a clear
    message instead of a raw `OSError`.
- Verified still fine by real use: Japanese-named folders register and
  resolve by name, deep (200+ byte) paths register, empty-registry
  `list` / `doctor` behave, and `init` rescues a git-less folder.
- Tests: 14 new tests in `tests/test_robustness.py` (31 total, all passing).

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
