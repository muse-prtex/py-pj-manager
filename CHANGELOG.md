# Changelog

> 24時間集中セッション（2026-11-16 01:08〜2026-11-17 01:08 JST）の総仕上げ：
> セッション1〜23で v0.3.0 → v0.24.0 へ進み、全174テストが通過、実使用フルコース
> （作成→登録→変更→コミット→状態確認）も確認済み。最終バージョンは **0.24.0**。
> 既知の残課題：`docs/images/` の PNG 7枚が GitHub 上に未反映（コネクタがバイナリを
> 扱えないため。Box の `docs-images-v0.12.0.zip` に実体あり。GitHub Web UI から
> `docs/images/` へドラッグ＆ドロップすれば usage.md と README の画像リンクが直る）。
> 週1回の改善（水曜）は `py-pj-manager-weekly-improvement` で継続。

## 0.25.0 — 2026-11-18

- `doctor` now reports `projects_root` as `fail` (exit 1) when the
  configured root exists as a file instead of a folder — \"フォルダでは
  なくファイルです: …\" / \"Not a folder — a file exists there: …\"
  with a hint to pick another folder via `config set-root`. Before,
  `doctor` said the root was \"ok (it will be created on first use)\"
  even though `create` fails against that path (v0.24.0 made `create
  --root` fail with a friendly message when the root is a file), so
  the two commands contradicted each other. A root that does not
  exist yet (with a writable parent) is still reported as ok.
- Real use: in the sandbox, set `projects_root` to an existing file
  and ran `doctor` (Japanese, English, `--json`) — `projects_root`
  is `fail` with the hint, exit 1; setting the root back to a folder
  returns `doctor` to ok. The weekly e2e (create with venv + git +
  initial commit, status/commit/log, push/pull against a local bare
  remote, register/unregister with the folder surviving, config
  save/load) all passed.
- Tests: 4 new tests in `tests/test_doctor.py` (core: file root fails
  in ja/en with the hint, missing-but-creatable root stays ok; CLI:
  `doctor --json` exits 1 with `projects_root` fail).

## 0.24.0 — 2026-11-17

- `create` with a `--root` that is a file, or whose path is blocked
  by a file, now fails with a friendly, localized message instead of
  Python's raw exception — \"作成先がフォルダではありません: …（ファイ
  ルが存在します。別の場所を指定してください）\" / \"The destination
  is not a folder: … (a file exists there. Pick another location)\"
  for a root that is a file, and \"作成先の途中にファイルがあります:
  …\" / \"A file blocks the destination path: …\" when an element of
  the path is a file (`FileExistsError: [Errno 17]` /
  `NotADirectoryError: [Errno 20]` before). A target name that
  already exists as a file is now reported as a file, not a folder
  (\"同じ名前のファイルがすでにあります: …\" / \"A file with the same
  name already exists: …\"). The failure stays a failure (exit 1):
  the destination is a caller error. The check runs in
  `core.create_project` before anything is created, so a failed
  attempt leaves no folder and no registry entry. The same idea as
  the empty commit message (v0.22.0) and the invalid `log -n` count
  (v0.23.0).
- Real use: in the sandbox, ran `create` with `--root` pointing at a
  file, at a path blocked by a file, and at a root where the target
  name is a file (Japanese, English, `--json`) — all exit 1 with the
  friendly message and no \"FileExistsError\" / \"Errno\"; a create
  with a good root still succeeds afterwards (screenshot
  `session22-create-root.png`).
- Tests: 9 new tests in `tests/test_create_root.py` (core: root is a
  file / parent is a file / target is a file, English, and a later
  good create; CLI: ja/en/JSON and exit codes).

## 0.23.0 — 2026-11-16

- `log -n` with a count of 0 or a negative number now fails with a
  friendly, localized message — "表示件数には1以上の整数を指定して
  ください（-n N）" / "Number of commits must be a positive integer
  (use -n N)" — instead of git's raw English "fatal: unrecognized
  argument: --1" (`-n -1` used to be passed to `git log` as "--1").
  `-n 0` used to succeed silently with an empty list. The failure
  stays a failure (exit 1): the count is a caller error. The check
  runs in `cli.cmd_log` before calling git, and before the empty-repo
  success path — an invalid count fails even on a repository with no
  commits yet. The same idea as the empty commit message (v0.22.0).
- Real use: in the sandbox, created a project, made a second commit,
  and ran `log` with `-n -1` and `-n 0` (Japanese, English,
  `--json`) — all exit 1 with the friendly message and no "fatal:";
  `-n 1` and the default still list the history normally (screenshot
  `session21-log-count.png`).
- Tests: 6 new tests in `tests/test_log_count.py` (CLI: -n -1 / -n 0
  fail friendly in ja/en/JSON with exit 1, fail on an empty repo too,
  and positive counts still list the right number of commits).

## 0.22.0 — 2026-11-16

- A `commit` with an empty commit message (`-m ""` or whitespace only)
  now fails with a friendly, localized message that says what to do
  next — "コミットメッセージが空です（-m \"メッセージ\" でコミット
  メッセージを指定してください）" / "Commit message is empty
  (specify one with -m \"message\")" — instead of git's raw English
  "Aborting commit due to empty commit message." The failure stays a
  failure (exit 1): the desired end state (a commit) is not met. The
  check happens in `core.commit_all` before `git add -A`, so a failed
  attempt leaves nothing staged, and it runs before the clean-tree
  check — an empty message is a caller error even on a clean tree.
  The same idea as the clean-tree commit (v0.17.0), the empty-repo log
  (v0.19.0), the no-remote / no-upstream push/pull (v0.20.0) and the
  no-identity commit (v0.21.0). Both GUIs already guard this on their
  side (tkinter returns early on an empty dialog answer; the desktop
  UI shows its inline `err_msg_required`), so the core check covers
  the CLI and agent callers.
- Real use: in the sandbox, created a project, changed a file, and
  ran `commit` with `-m ""` and `-m "   "` (Japanese, English,
  `--json`) — all exit 1 with the friendly message and no "Aborting
  commit", nothing staged, no extra commit; a real message afterwards
  commits normally (screenshot `session20-commit-msg.png`).
- Tests: 8 new tests in `tests/test_commit_message.py` (core: empty /
  whitespace-only messages fail friendly in ja/en, leave nothing
  staged and no extra commit, fail even on a clean tree, and a real
  message still commits afterwards; CLI: ja/en/JSON with exit 1).

## 0.21.0 — 2026-11-16

- A `commit` with git user.name / user.email not set now fails with a
  friendly, localized message that says what to do next, instead of
  git's raw English "Author identity unknown / Please tell me who you
  are" (exit 128). The commands still fail (exit 1) — the desired end
  state (a commit) is not met — but now report "git のユーザー名・
  メールアドレスが設定されていません（`git config --global user.name
  \"名前\"` と `git config --global user.email \"メール\"` で設定して
  ください）" / "git user.name / user.email is not set …". Detection
  is `core.git_identity_configured()` via `git config user.name` /
  `user.email` exit codes (plus the GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL
  and GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL fallbacks git itself
  honors), so it does not depend on git's message text (which changes
  with locale). The same idea as the clean-tree commit (v0.17.0), the
  empty-repo log (v0.19.0) and the no-remote / no-upstream push/pull
  (v0.20.0). A commit on a clean tree still succeeds even with no
  identity set — there is nothing to commit, so the check is skipped.
  The tkinter GUI's commit button uses the same path
  (`core.commit_all`), so it shows the friendly message too.
- `doctor` gains a `git_identity` check: it looks at the *global*
  user.name / user.email (`git config --global`) and warns when they
  are not set, with a hint giving the two `git config --global`
  commands (and a note that per-repository settings are fine — the
  commit path checks the effective identity, so a per-repository
  identity still works). The desktop UI's demo doctor data includes
  the new check.
- Real use: in the sandbox, isolated git from the global config
  (GIT_CONFIG_GLOBAL=/dev/null) and ran `commit` (Japanese, English,
  `--json`) — all exit 1 with the friendly message and no "Author
  identity unknown" / "fatal:"; setting the identity once (locally or
  globally) makes the commit succeed, and a clean tree still commits
  successfully with no identity at all (screenshot
  `session19-identity.png`). `doctor` warns with the same hint under
  the isolated config and is ok with the normal config.
- Tests: 12 new tests in `tests/test_git_identity.py`
  (`git_identity_configured` with local / global / env-var identity
  and with none of them, `commit_all` failing friendly in ja/en/JSON
  with no identity, succeeding on a clean tree with no identity,
  succeeding once the identity is set, CLI exit codes, and the
  `doctor` git_identity check ok/warn in both core and CLI form).
  151 tests total, all passing.
- `day-run/tools/session19-identity.sh` — the real-use demo for this
  session (create, commit with no identity in ja/en/JSON, set the
  identity and commit, clean-tree commit with no identity, doctor
  warn/ok). Shot with `term_shot.py`.

## 0.20.0 — 2026-11-16

- `push` / `pull` with no remote or no upstream branch configured now
  fail with a friendly, localized message that says what to do next,
  instead of git's raw English output. A freshly created project has a
  local repository with no remote, so `push` used to exit 1 with
  "fatal: No configured push destination." and `pull` with "There is no
  tracking information for the current branch."; with a remote added but
  no upstream, `push` failed with "The current branch main has no
  upstream branch.". The commands still fail (exit 1) — the desired end
  state (pushed / pulled) is not met — but now report
  "リモートが設定されていません（`git remote add origin <URL>` で追加
  してください）" / "No remote is configured …" when no remote exists,
  and "上流ブランチが設定されていません（`git push --set-upstream
  origin main` で設定してください）" / "No upstream branch is
  configured …" (for `pull`: "`git pull origin main` で取り込むか…")
  when a remote exists but the branch tracks none. The same idea as
  the clean-tree commit (v0.17.0) and the empty-repo log (v0.19.0).
  Detection is `core.upstream_state()` via `git remote` and
  `git rev-parse @{u}` exit codes, so it does not depend on git's
  message text (which changes with locale). A real failure (an
  unreachable remote, an authentication error) still passes git's
  output through unchanged, and a repository with no commits yet keeps
  git's own message. The tkinter GUI's push / pull buttons use the same
  path (`core.git_push_pull`), so they show the friendly message too.
- Real use: in the sandbox, created a project and ran `push` / `pull`
  with no remote (Japanese, English, `--json`), then added a bare
  remote and ran both again with no upstream — all exit 1 with the
  friendly message and no "fatal:"; setting the upstream once makes
  `push` succeed (screenshot `session18-push.png`).
- Tests: 15 new tests in `tests/test_push_pull.py` (`upstream_state`
  in all three states, friendly messages in ja/en/JSON for both
  commands, push still succeeding with an upstream, unreachable
  remote staying raw, empty repo staying raw). 139 tests total, all
  passing.
- `day-run/tools/session18-push.sh` — the real-use demo for this
  session (create, push/pull with no remote, add a bare remote,
  push/pull with no upstream, English display, then push with an
  upstream set); run it through `term_shot.py` to re-take the
  screenshot.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed with
  the GitHub connector — `push_files` / `create_or_update_file` accept
  UTF-8 text only. The images are in Box as `docs-images-v0.12.0.zip`
  (`12_Muse/PJマネージャー`); adding them via the GitHub web UI to
  `docs/images/` fixes the links in `docs/usage.md` and the READMEs.

## 0.19.0 — 2026-11-16

- `log` on a repository with no commits yet no longer fails. It used to
  exit 1 with git's raw English output ("fatal: your current branch
  'main' does not have any commits yet") — easy to hit, because `init`
  creates a repository with no commits. An empty history is not a
  failure, so `log` now succeeds (exit 0) with an empty list
  (`{"ok": true, "log": []}` with `--json`) and a friendly localized
  message ("まだコミットがありません" / "No commits yet"). The same
  idea as committing a clean tree (v0.17.0): the desired end state is
  already met. Detection is `core.has_commits()` via
  `git rev-parse --verify HEAD`, so it depends on the exit code, not on
  git's message text (which changes with locale). A real failure (a
  corrupt repository, a non-git folder) still fails as before.
- Real use: in the sandbox, registered and `init`-ed an empty project
  and ran `log` in Japanese, in English and with `--json` — all exit 0
  with the empty list / message; a committed project still lists its
  history and `-n 1` still limits it (screenshot `session17-log.png`).
- Tests: 8 new tests in `tests/test_log.py` (`has_commits` before /
  after the first commit, CLI `log` on an empty repo in ja/en/JSON,
  history still listed, `-n` limiting, non-git folder still fails).
  124 tests total, all passing.
- `day-run/tools/session17-log.sh` — the real-use demo for this
  session (register + init an empty project, `log` it in ja/en/JSON,
  then `log` a committed project with `-n 1`); run it through
  `term_shot.py` to re-take the screenshot.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed with
  the GitHub connector — `push_files` / `create_or_update_file` accept
  UTF-8 text only. The images are in Box as `docs-images-v0.12.0.zip`
  (`12_Muse/PJマネージャー`); adding them via the GitHub web UI to
  `docs/images/` fixes the links in `docs/usage.md` and the READMEs.

## 0.18.0 — 2026-11-16

- `status` on a registered project whose folder is gone (a "ghost") no
  longer reports success. It used to exit 0 with "git: not a repository"
  — misleading, because the folder does not exist at all; it is not a
  non-git folder. `status` now fails (exit 1) with the localized
  folder-missing message ("フォルダがありません: …" / "Folder not found:
  …"), in human output and as `{"ok": false, "error": ...}` with
  `--json` — the same message the git commands already use, and the same
  idea as `check`, where a missing folder makes the whole result not-ok.
  `list` now marks a ghost row `[missing]` in human output, so a ghost no
  longer looks identical to a live project; the JSON is unchanged and
  still carries `exists: false`.
- Real use: in the sandbox, created ghost-demo and live-demo, deleted
  ghost-demo's folder, and ran `status` / `list` in Japanese, in English
  and with `--json` — the ghost fails with exit 1 in all three forms, the
  live project still reports normally (screenshot `session16-status.png`).
- Tests: 7 new tests in `tests/test_status_missing.py` (ghost fails in
  ja/en/JSON, live still ok, unregistered missing path keeps the old
  "project not found" error, `list` marks the ghost, JSON keeps
  `exists: false`); the old robustness test that asserted the old
  `status`-on-ghost behaviour was updated to the new one. 116 tests
  total, all passing.
- `day-run/tools/session16-status.sh` — the real-use demo for this
  session (create two projects, delete one folder, run `status` / `list`
  in ja/en/JSON); run it through `term_shot.py` to re-take the
  screenshot.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed with
  the GitHub connector — `push_files` / `create_or_update_file` accept
  UTF-8 text only. The images are in Box as `docs-images-v0.12.0.zip`
  (`12_Muse/PJマネージャー`); adding them via the GitHub web UI to
  `docs/images/` fixes the links in `docs/usage.md` and the READMEs.

## 0.17.0 — 2026-11-16

- Committing a clean tree is no longer a failure. `commit` used to exit 1
  with git's raw English output ("On branch main / nothing to commit,
  working tree clean") when there was nothing to commit — the desktop
  UI's commit modal showed an error dialog for what is really the
  desired end state. `core.commit_all()` now returns success with a
  friendly localized message ("コミットする変更はありません（作業ツリー
  はクリーンです）" / "Nothing to commit (working tree clean)") when the
  commit fails but the tree is clean afterwards; a real failure (a hook
  rejecting the commit, missing git identity, …) still fails, because
  staged changes remain and the tree is not clean. Detection uses the
  dirty count from `git_status`, not git's message text, so it does not
  depend on git's locale.
- Real use: in the sandbox, committed a real change, then committed the
  same clean tree again — exit 0 in Japanese, in English, and with
  `--json` (`{"ok": true, ...}`), and the log shows no extra commit was
  created (screenshot `session15-commit.png`).
- Tests: 7 new tests in `tests/test_commit.py` (clean tree succeeds in
  both languages, a real change still creates a commit, a failing
  pre-commit hook still fails, CLI exit code / JSON / human output).
  109 tests total, all passing.
- `day-run/tools/session15-commit.sh` — the real-use demo for this
  session (create → change → commit → commit the clean tree in ja/en/JSON,
  with the commit log at the end); run it through `term_shot.py` to
  re-take the screenshot.
- Note: the 7 screenshots in `docs/images/` still cannot be pushed with
  the GitHub connector — `push_files` / `create_or_update_file` accept
  UTF-8 text only. The images are in Box as `docs-images-v0.12.0.zip`
  (`12_Muse/PJマネージャー`); adding them via the GitHub web UI to
  `docs/images/` fixes the links in `docs/usage.md` and the READMEs.

## 0.16.0 — 2026-11-16

- Desktop UI language audit: three values the CLI returns raw were shown
  untranslated — the doctor status (`warn` stayed English in the Japanese
  sidebar line and in the log's doctor items) and the project's origin
  (`created` / `existing` in the detail line). They now go through the
  `I18N` dictionary (`status_ok` / `status_warn` / `status_fail`,
  `origin_created` / `origin_existing`) via new `statusText()` /
  `originText()` helpers, with unknown values passed through unchanged.
  The demo data's `gamma-legacy` also used an origin (`registered`) the
  CLI never returns; it is now `existing`, matching the real contract.
- Real use: opened the desktop UI in the browser demo and verified both
  languages — Japanese shows 「環境チェック: 注意（7 ok / 1 warn / 0 fail）」
  and 「登録日: 2026-11-16（作成）」, English shows
  "Environment check: warn (7 ok / 1 warn / 0 fail)" and
  "Registered: 2026-11-16 (created)" (screenshots
  `session14-desktop.png`, `session14-desktop-en.png`).
- Tests: 2 new tests in `tests/test_desktop_ui.py` (static wiring of
  `statusText` / `originText` plus demo-origin values, and a node-run
  check of the actual translations in both languages incl. unknown-value
  pass-through). 102 tests total, all passing.
- `day-run/tools/desktop_shot.py` now asserts the doctor line and the
  detail line in both languages (still 7 shots total).

## 0.15.0 — 2026-11-16

- The Tauri desktop UI now follows the display language (ja / en) like
  the CLI and the tkinter GUI do. A **言語 / Language** dropdown sits at
  the bottom-left of the sidebar; switching it calls
  `config set-language`, so the choice is shared with the CLI and the
  tkinter GUI (in the browser demo it is kept in localStorage instead,
  and `?lang=en` opens the English view directly). All UI strings live
  in one `I18N` dictionary inside `desktop/ui/index.html` — static text
  via `data-i18n` / `data-i18n-placeholder`, dynamic text (badges, chips,
  detail lines, doctor line, log lines, modal errors, confirm dialogs)
  via `t(key, {...})`; the demo doctor data is built from the dictionary
  so it translates too. The log's already-written lines keep the language
  they were written in; everything new follows the current language.
- Real use: opened the desktop UI in the browser demo, switched the
  language with the sidebar dropdown (verified: the button text became
  "+ New project"), and opened `?lang=en` / `?demo=empty&lang=en`
  directly — the main view and the empty state are fully English
  (screenshots `session13-desktop-en.png`, `session13-empty-en.png`).
  Found and fixed while verifying: the version line under the sidebar
  stayed Japanese after switching, because it was set once at startup;
  `applyLanguage()` now re-renders it (guarded by a test).
- Tests: 6 new tests in `tests/test_desktop_ui.py` (dictionary
  completeness incl. placeholder parity, every `data-i18n` key exists,
  no orphan dictionary keys, dynamic strings go through `t()`, version
  line re-render). 100 tests total, all passing.
- `day-run/tools/desktop_shot.py` now also takes the English main view
  and the English empty state (7 shots total) and asserts the language
  switch actually changes the button text.

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
