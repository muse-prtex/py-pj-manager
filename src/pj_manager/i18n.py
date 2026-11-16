#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pj_manager/i18n.py — UI 文字列の辞書と表示言語の解決。

言語切替の下地（v0.11.0）。CLI の人間向け出力と tkinter GUI の
表示文字列は、ここにある辞書だけを参照する。JSON 出力のキーや
プロジェクト名・パスなどの値は言語に依存しない。

- 表示言語は config.json の `language`（"ja" 既定 / "en"）。
  知らない値は "ja" に倒す。
- core.py / cli.py / app.py は `i18n.t(key, lang=..., **kw)` で
  文字列を取る。core は自分の CONFIG_FILE を渡すので、テストの
  monkey-patch でもサンドボックスの言語が使われる。
- デスクトップ UI（desktop/ui/index.html）の文字列も v0.15.0 で辞書化
  した（同ファイル内の `I18N` と `t()`、`data-i18n` 属性）。
  言語は config.json の `language` を `config set-language` で共有する。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from string import Formatter

LANGUAGES = ("ja", "en")
DEFAULT_LANGUAGE = "ja"

# config.json の置き場: core.py と同じ決め方（環境変数があればそこ、
# なければこのファイルから2つ上＝リポジトリのルート）。core への
# 循環 import を避けるため、ここで同じ3行だけ重ねている。
_env_data = os.environ.get("PJ_MANAGER_DATA_DIR")
_DATA_DIR = (Path(_env_data).expanduser() if _env_data
             else Path(__file__).resolve().parents[2])
_DEFAULT_CONFIG_FILE = _DATA_DIR / "config.json"


def normalize_language(value) -> str:
    """言語コードを "ja" / "en" に正規化する。知らない値は "ja"。"""
    if isinstance(value, str) and value.strip().lower() in LANGUAGES:
        return value.strip().lower()
    return DEFAULT_LANGUAGE


def get_language(config_file: Path | None = None) -> str:
    """config.json の `language` を読む。無ければ・読めなければ "ja"。"""
    path = Path(config_file) if config_file is not None else _DEFAULT_CONFIG_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return DEFAULT_LANGUAGE
    if isinstance(data, dict):
        return normalize_language(data.get("language"))
    return DEFAULT_LANGUAGE


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """辞書から文字列を取り、{placeholder} を埋めて返す。

    lang を省略すると config.json の言語を使う。知らないキーは
    KeyError（テストで全参照キーの存在を保証する）にする。
    """
    lang = normalize_language(lang) if lang else get_language()
    text = STRINGS[key][lang]
    return text.format(**kwargs) if kwargs else text


def check_dictionaries() -> list[str]:
    """辞書の自己点検。問題があれば説明のリストを返す（無ければ空）。

    - ja / en のキーが一致すること
    - どちらも空文字列でないこと
    - {placeholder} の名前が ja / en で一致すること
    """
    problems: list[str] = []
    keys = set(STRINGS)
    fmt = Formatter()
    for key in sorted(keys):
        entry = STRINGS[key]
        for lang in LANGUAGES:
            if lang not in entry:
                problems.append(f"{key}: missing {lang}")
                continue
            if not entry[lang]:
                problems.append(f"{key}: empty {lang}")
        if all(lang in entry for lang in LANGUAGES):
            ph_ja = {name for _, name, _, _ in fmt.parse(entry["ja"]) if name}
            ph_en = {name for _, name, _, _ in fmt.parse(entry["en"]) if name}
            if ph_ja != ph_en:
                problems.append(
                    f"{key}: placeholders differ ja={sorted(ph_ja)} "
                    f"en={sorted(ph_en)}")
    return problems


STRINGS: dict[str, dict[str, str]] = {
    # ---------- core.run_cmd ----------
    "folder_missing": {
        "ja": "フォルダがありません: {path}",
        "en": "Folder not found: {path}",
    },
    "command_not_found": {
        "ja": "コマンドが見つかりません: {cmd}",
        "en": "Command not found: {cmd}",
    },
    "timeout": {
        "ja": "タイムアウトしました（600秒）",
        "en": "Timed out (600 seconds)",
    },
    # ---------- core.register_existing / create_project ----------
    "already_registered": {
        "ja": "すでに登録されています: {name}",
        "en": "Already registered: {name}",
    },
    "duplicate_name_register": {
        "ja": "同じ名前のプロジェクトがすでに登録されています: {name} "
              "（{path}）。フォルダ名を変えるか先に unregister してください",
        "en": "A project with the same name is already registered: {name} "
              "({path}). Rename the folder or unregister it first",
    },
    "invalid_name": {
        "ja": "プロジェクト名は半角英数字・ハイフン・アンダースコアで、"
              "英数字から始めてください（フォルダ名になります）",
        "en": "Project names must use letters, digits, hyphens or "
              "underscores and start with a letter or digit "
              "(it becomes the folder name)",
    },
    "name_too_long": {
        "ja": "プロジェクト名が長すぎます（255バイト以内にしてください）",
        "en": "Project name is too long (keep it within 255 bytes)",
    },
    "duplicate_name_create": {
        "ja": "同じ名前のプロジェクトがすでに登録されています: {name} "
              "（{path}）。別の名前にしてください",
        "en": "A project with the same name is already registered: {name} "
              "({path}). Pick another name",
    },
    "folder_exists": {
        "ja": "同じ名前のフォルダがすでにあります: {path}",
        "en": "A folder with the same name already exists: {path}",
    },
    "log_folder_created": {
        "ja": "フォルダを作成: {path}",
        "en": "Created folder: {path}",
    },
    "log_template_placed": {
        "ja": "テンプレート（Python）を配置しました",
        "en": "Placed the Python template",
    },
    "log_venv_creating": {
        "ja": "venv を作成中…（少し時間がかかります）",
        "en": "Creating the venv… (this takes a moment)",
    },
    "log_venv_created": {
        "ja": "venv を作成しました",
        "en": "Created the venv",
    },
    "log_venv_failed": {
        "ja": "venv 作成に失敗: {out}",
        "en": "Failed to create the venv: {out}",
    },
    "log_git_skip_no_git": {
        "ja": "git が入っていないため、git init をスキップしました",
        "en": "Skipped git init because git is not installed",
    },
    "log_git_init": {
        "ja": "git init しました",
        "en": "Ran git init",
    },
    "log_first_commit": {
        "ja": "最初のコミットを作成しました",
        "en": "Created the initial commit",
    },
    "log_first_commit_skip": {
        "ja": "最初のコミットはスキップしました。"
              "（git のユーザー名/メール未設定などの場合は、設定後にコミットしてください）",
        "en": "Skipped the initial commit. "
              "(If git user.name / user.email is not set, "
              "commit after setting them)",
    },
    "core_nothing_to_commit": {
        "ja": "コミットする変更はありません（作業ツリーはクリーンです）",
        "en": "Nothing to commit (working tree clean)",
    },
    "log_registered": {
        "ja": "プロジェクト一覧に登録しました",
        "en": "Registered the project in the list",
    },
    "log_github_created": {
        "ja": "GitHub リポジトリを作成しました（{visibility}）",
        "en": "Created the GitHub repository ({visibility})",
    },
    "log_github_failed": {
        "ja": "GitHub 作成に失敗: {out}",
        "en": "Failed to create the GitHub repository: {out}",
    },
    "log_github_project_ok": {
        "ja": "プロジェクト自体はできています。後から一覧のボタンでも作成できます",
        "en": "The project itself is ready. "
              "You can create the repository later from the list",
    },
    # ---------- core.gh ----------
    "gh_not_installed": {
        "ja": "gh CLI が入っていません（https://cli.github.com/ からインストール）",
        "en": "gh CLI is not installed "
              "(install it from https://cli.github.com/)",
    },
    "gh_not_logged_in": {
        "ja": "gh にログインしていません。ターミナルで `gh auth login` を実行してください",
        "en": "Not logged in to gh. Run `gh auth login` in a terminal",
    },
    "origin_already_set": {
        "ja": "すでに origin が設定されています",
        "en": "origin is already set",
    },
    # ---------- core.doctor ----------
    "doctor_python_old": {
        "ja": "Python {version}（3.10 以上が必要です）",
        "en": "Python {version} (3.10 or later is required)",
    },
    "doctor_venv_ok": {
        "ja": "venv モジュールが使えます",
        "en": "The venv module is available",
    },
    "doctor_venv_missing": {
        "ja": "venv モジュールがありません",
        "en": "The venv module is missing",
    },
    "doctor_git_missing": {
        "ja": "git が見つかりません",
        "en": "git was not found",
    },
    "doctor_git_missing_hint": {
        "ja": "git を入れると git init / コミットなどの機能が使えます",
        "en": "Install git to use git init, commit and other git features",
    },
    "doctor_gh_ok": {
        "ja": "gh CLI にログイン済みです",
        "en": "Logged in to the gh CLI",
    },
    "doctor_gh_not_logged_in": {
        "ja": "gh CLI はありますがログインしていません",
        "en": "gh CLI is installed but not logged in",
    },
    "doctor_gh_not_logged_in_hint": {
        "ja": "ターミナルで `gh auth login` を実行してください",
        "en": "Run `gh auth login` in a terminal",
    },
    "doctor_gh_missing": {
        "ja": "gh CLI が入っていません",
        "en": "gh CLI is not installed",
    },
    "doctor_gh_missing_hint": {
        "ja": "GitHub 機能を使う場合は https://cli.github.com/ からインストール",
        "en": "To use GitHub features, install it from https://cli.github.com/",
    },
    "doctor_root_ok": {
        "ja": "存在します: {path}",
        "en": "Exists: {path}",
    },
    "doctor_root_will_create": {
        "ja": "まだありません（初回作成時に作られます）: {path}",
        "en": "Not created yet (it will be created on first use): {path}",
    },
    "doctor_root_fail": {
        "ja": "作れません: {path}",
        "en": "Cannot be created: {path}",
    },
    "doctor_root_fail_hint": {
        "ja": "config set-root で書き込めるフォルダを指定してください",
        "en": "Use `config set-root` to point at a writable folder",
    },
    "doctor_data_ok": {
        "ja": "書き込めます: {path}",
        "en": "Writable: {path}",
    },
    "doctor_data_fail": {
        "ja": "書き込めません: {path} ({error})",
        "en": "Not writable: {path} ({error})",
    },
    "doctor_registry_corrupt": {
        "ja": "projects.json が読めません（壊れている可能性があります）",
        "en": "projects.json cannot be read (it may be corrupt)",
    },
    "doctor_registry_corrupt_hint": {
        "ja": "projects.json を削除すると空の登録簿から始められます"
              "（登録だけが消え、フォルダは残ります）",
        "en": "Delete projects.json to start from an empty registry "
              "(only registrations are lost; folders stay)",
    },
    "doctor_registry_malformed": {
        "ja": "{count} 件登録中・読み取れない登録が {malformed} 件あります",
        "en": "{count} registered, {malformed} unreadable entries",
    },
    "doctor_registry_malformed_hint": {
        "ja": "次に登録簿を保存するとき、読み取れない登録は "
              "projects.json.bak-<日時> に退避されます",
        "en": "When the registry is next saved, unreadable entries are "
              "moved to projects.json.bak-<timestamp>",
    },
    "doctor_registry_dupes": {
        "ja": "同じ名前の登録が重複しています: {names}",
        "en": "Duplicate registrations with the same name: {names}",
    },
    "doctor_registry_dupes_hint": {
        "ja": "名前で区別できないため、片方を unregister してください",
        "en": "Unregister one of them, since commands address projects by name",
    },
    "doctor_registry_missing": {
        "ja": "{count} 件登録中・うちフォルダが無いもの: {names}",
        "en": "{count} registered, folders missing for: {names}",
    },
    "doctor_registry_missing_hint": {
        "ja": "存在しないフォルダの登録は unregister で外せます",
        "en": "Unregister the registrations whose folders no longer exist",
    },
    "doctor_registry_ok": {
        "ja": "{count} 件登録中（フォルダは全て存在します）",
        "en": "{count} registered (all folders exist)",
    },
    "doctor_registry_empty": {
        "ja": "登録はまだありません（空です）",
        "en": "No projects registered yet (empty)",
    },
    "doctor_registry_absent": {
        "ja": "まだありません（初回登録時に作られます）",
        "en": "Not created yet (it will be created on first registration)",
    },
    "doctor_config_unreadable": {
        "ja": "config.json が読めません（既定値で動きます）",
        "en": "config.json cannot be read (using defaults)",
    },
    "doctor_config_unreadable_hint": {
        "ja": "config.json を削除すると既定値に戻ります",
        "en": "Delete config.json to restore the defaults",
    },
    "doctor_config_ok": {
        "ja": "config.json が読めます",
        "en": "config.json is readable",
    },
    "doctor_config_absent": {
        "ja": "まだありません（既定値で動きます）",
        "en": "Not created yet (using defaults)",
    },
    # ---------- cli.py（人間向け出力。もとから英語のものも辞書化して統一） ----------
    "cli_no_projects": {
        "ja": "(no projects registered)",
        "en": "(no projects registered)",
    },
    "cli_created": {
        "ja": "created: {path}",
        "en": "created: {path}",
    },
    "cli_registered": {
        "ja": "registered: {name} ({path})",
        "en": "registered: {name} ({path})",
    },
    "cli_unregistered": {
        "ja": "unregistered: {name} (folder kept)",
        "en": "unregistered: {name} (folder kept)",
    },
    "cli_no_registration": {
        "ja": "登録がありません: {name}",
        "en": "No such registration: {name}",
    },
    "cli_status_venv": {
        "ja": "venv: {value}",
        "en": "venv: {value}",
    },
    "cli_status_git": {
        "ja": "git: branch={branch} dirty={dirty} ahead={ahead} behind={behind}",
        "en": "git: branch={branch} dirty={dirty} ahead={ahead} behind={behind}",
    },
    "cli_status_last": {
        "ja": "last: {last}",
        "en": "last: {last}",
    },
    "cli_status_not_git": {
        "ja": "git: not a repository",
        "en": "git: not a repository",
    },
    "cli_list_missing": {
        "ja": "missing",
        "en": "missing",
    },
    "cli_not_git_repo": {
        "ja": "git リポジトリではありません: {path}"
              "（先に `init` で git 初期化してください）",
        "en": "Not a git repository: {path} "
              "(run `init` first to initialize git)",
    },
    "cli_commit_failed": {
        "ja": "commit failed",
        "en": "commit failed",
    },
    "cli_git_op_failed": {
        "ja": "git {op} failed",
        "en": "git {op} failed",
    },
    "cli_no_remote": {
        "ja": "リモートが設定されていません"
              "（`git remote add origin <URL>` で追加してください）",
        "en": "No remote is configured "
              "(add one with `git remote add origin <URL>`)",
    },
    "cli_no_upstream_push": {
        "ja": "上流ブランチが設定されていません"
              "（`git push --set-upstream origin {branch}` で設定してください）",
        "en": "No upstream branch is configured "
              "(set it with `git push --set-upstream origin {branch}`)",
    },
    "cli_no_upstream_pull": {
        "ja": "上流ブランチが設定されていません"
              "（`git pull origin {branch}` で取り込むか、"
              "`git branch --set-upstream-to=origin/{branch} {branch}` で設定してください）",
        "en": "No upstream branch is configured "
              "(run `git pull origin {branch}` to fetch, or set it with "
              "`git branch --set-upstream-to=origin/{branch} {branch}`)",
    },
    "cli_log_failed": {
        "ja": "git log failed",
        "en": "git log failed",
    },
    "cli_log_empty": {
        "ja": "まだコミットがありません",
        "en": "No commits yet",
    },
    "cli_init_failed": {
        "ja": "git init failed",
        "en": "git init failed",
    },
    "cli_already_git": {
        "ja": "already a git repository",
        "en": "already a git repository",
    },
    "cli_check_summary": {
        "ja": "check: {total} projects "
              "({ok} ok / {attention} attention / {missing} missing)",
        "en": "check: {total} projects "
              "({ok} ok / {attention} attention / {missing} missing)",
    },
    "cli_doctor_status": {
        "ja": "status: {status} ({ok} ok / {warn} warn / {fail} fail)",
        "en": "status: {status} ({ok} ok / {warn} warn / {fail} fail)",
    },
    "cli_config_root_set": {
        "ja": "projects_root: {value}",
        "en": "projects_root: {value}",
    },
    "cli_set_language": {
        "ja": "language: {value}",
        "en": "language: {value}",
    },
    "cli_invalid_language": {
        "ja": "言語は ja か en を指定してください: {value}",
        "en": "Language must be ja or en: {value}",
    },
    "cli_unknown_config_action": {
        "ja": "unknown config action: {action}",
        "en": "unknown config action: {action}",
    },
    "cli_project_not_found": {
        "ja": "プロジェクトが見つかりません: {target}",
        "en": "Project not found: {target}",
    },
    # ---------- app.py（tkinter GUI） ----------
    "app_title": {
        "ja": "PJマネージャー — プロジェクト総合管理",
        "en": "PJ Manager — Project Management",
    },
    "app_sidebar_title": {
        "ja": "PJマネージャー",
        "en": "PJ Manager",
    },
    "app_section_projects": {
        "ja": "プロジェクト",
        "en": "Projects",
    },
    "app_btn_new": {
        "ja": "＋ 新規プロジェクト作成",
        "en": "+ New project",
    },
    "app_btn_register": {
        "ja": "既存フォルダを登録",
        "en": "Register existing folder",
    },
    "app_btn_unregister": {
        "ja": "登録を外す",
        "en": "Unregister",
    },
    "app_btn_config": {
        "ja": "作成先フォルダの設定",
        "en": "Set projects folder",
    },
    "app_language_label": {
        "ja": "言語",
        "en": "Language",
    },
    "app_shortcuts_hint": {
        "ja": "ショートカット: Ctrl+N 新規作成 / Ctrl+O 登録 / F5・Ctrl+R 更新 / Enter ターミナル / Del 登録解除 / Ctrl+Q 終了",
        "en": "Shortcuts: Ctrl+N New / Ctrl+O Register / F5, Ctrl+R Refresh / Enter Terminal / Del Unregister / Ctrl+Q Quit",
    },
    "app_detail_placeholder": {
        "ja": "左の一覧からプロジェクトを選んでください",
        "en": "Select a project from the list",
    },
    "app_section_open": {
        "ja": "開く",
        "en": "Open",
    },
    "app_btn_terminal": {
        "ja": "ターミナルで開く（venv有効化）",
        "en": "Open terminal (with venv)",
    },
    "app_btn_vscode": {
        "ja": "VS Codeで開く",
        "en": "Open in VS Code",
    },
    "app_btn_folder": {
        "ja": "フォルダを開く",
        "en": "Open folder",
    },
    "app_btn_refresh": {
        "ja": "状態を更新",
        "en": "Refresh status",
    },
    "app_btn_commit": {
        "ja": "コミット",
        "en": "Commit",
    },
    "app_btn_push": {
        "ja": "プッシュ",
        "en": "Push",
    },
    "app_btn_pull": {
        "ja": "プル",
        "en": "Pull",
    },
    "app_btn_log": {
        "ja": "ログ（最近10件）",
        "en": "Log (last 10)",
    },
    "app_btn_git_init": {
        "ja": "git init",
        "en": "git init",
    },
    "app_btn_gh_create": {
        "ja": "リポジトリを作成",
        "en": "Create repository",
    },
    "app_btn_gh_open": {
        "ja": "ブラウザで開く",
        "en": "Open in browser",
    },
    "app_log_label": {
        "ja": "実行ログ",
        "en": "Run log",
    },
    "app_folder_missing_mark": {
        "ja": "（フォルダなし）",
        "en": " (folder missing)",
    },
    "app_detail_name": {
        "ja": "名前: {name}",
        "en": "Name: {name}",
    },
    "app_detail_location": {
        "ja": "場所: {path}",
        "en": "Location: {path}",
    },
    "app_detail_registered": {
        "ja": "登録日: {date}（{origin}）",
        "en": "Registered: {date} ({origin})",
    },
    "app_detail_venv": {
        "ja": "venv: {value}",
        "en": "venv: {value}",
    },
    "app_detail_git": {
        "ja": "Git: ブランチ {branch} / 未コミット {dirty} 件"
              " / 未プッシュ {ahead} 件 / 未プル {behind} 件",
        "en": "Git: branch {branch} / {dirty} uncommitted"
              " / {ahead} unpushed / {behind} unpulled",
    },
    "app_detail_last_commit": {
        "ja": "最終コミット: {last}",
        "en": "Last commit: {last}",
    },
    "app_detail_github": {
        "ja": "GitHub: {url}",
        "en": "GitHub: {url}",
    },
    "app_detail_not_connected": {
        "ja": "未接続",
        "en": "Not connected",
    },
    "app_detail_not_git": {
        "ja": "Git: 管理外（「git init」ボタンで開始できます）",
        "en": "Git: not a repository (use the “git init” button to start)",
    },
    "app_detail_folder_missing": {
        "ja": "フォルダが見つかりません（移動・削除された可能性）",
        "en": "Folder not found (it may have been moved or deleted)",
    },
    "app_msg_not_selected_title": {
        "ja": "未選択",
        "en": "Not selected",
    },
    "app_msg_not_selected": {
        "ja": "まず左の一覧からプロジェクトを選んでください",
        "en": "Select a project from the list first",
    },
    "app_log_error": {
        "ja": "エラー: {error}",
        "en": "Error: {error}",
    },
    "app_log_terminal_opened": {
        "ja": "{name}: ターミナルを開きました",
        "en": "{name}: opened a terminal",
    },
    "app_vscode_not_found": {
        "ja": "VS Code の `code` コマンドが見つかりません",
        "en": "VS Code `code` command not found",
    },
    "app_vscode_opened": {
        "ja": "VS Code で開きました",
        "en": "Opened in VS Code",
    },
    "app_log_header": {
        "ja": "--- ログ ---",
        "en": "--- Log ---",
    },
    "app_log_failed": {
        "ja": "失敗: {out}",
        "en": "Failed: {out}",
    },
    "app_log_already_git": {
        "ja": "すでに git 管理下です",
        "en": "Already a git repository",
    },
    "app_git_success": {
        "ja": "成功",
        "en": "Success",
    },
    "app_git_failed": {
        "ja": "失敗",
        "en": "Failed",
    },
    "app_git_no_output": {
        "ja": "（出力なし）",
        "en": "(no output)",
    },
    "app_gh_create_title": {
        "ja": "GitHubリポジトリ作成",
        "en": "Create GitHub repository",
    },
    "app_gh_create_log": {
        "ja": "GitHub作成: {name}",
        "en": "Create GitHub repository: {name}",
    },
    "app_gh_create_body": {
        "ja": "{name} のGitHubリポジトリを Private で作成します。よろしいですか？\n"
              "（Publicにしたい場合は README のコマンド例をご覧ください）",
        "en": "Create a Private GitHub repository for {name}?\n"
              "(For Public, see the command examples in the README)",
    },
    "app_gh_url_unknown": {
        "ja": "GitHub の URL が分かりません（origin 未設定か、GitHub以外のリモートです）",
        "en": "GitHub URL unknown (origin not set, or a non-GitHub remote)",
    },
    "app_unregister_title": {
        "ja": "登録を外す",
        "en": "Unregister",
    },
    "app_unregister_body": {
        "ja": "{name} の登録を外しますか？\nフォルダ自体は消えません。",
        "en": "Unregister {name}? The folder itself will not be deleted.",
    },
    "app_log_unregistered": {
        "ja": "{name}: 登録を外しました",
        "en": "{name}: unregistered",
    },
    "app_register_dialog_title": {
        "ja": "登録するプロジェクトのフォルダ",
        "en": "Folder of the project to register",
    },
    "app_register_error_title": {
        "ja": "登録できません",
        "en": "Cannot register",
    },
    "app_log_registered": {
        "ja": "登録しました: {name}",
        "en": "Registered: {name}",
    },
    "app_config_dialog_title": {
        "ja": "新規プロジェクトの作成先フォルダ",
        "en": "Folder for new projects",
    },
    "app_log_root_set": {
        "ja": "作成先フォルダを {folder} にしました",
        "en": "Set the projects folder to {folder}",
    },
    "app_new_dialog_title": {
        "ja": "新規プロジェクト作成",
        "en": "New project",
    },
    "app_new_name_label": {
        "ja": "プロジェクト名（半角英数字・-・_）",
        "en": "Project name (letters, digits, -, _)",
    },
    "app_new_root_label": {
        "ja": "作成先: {root}",
        "en": "Create in: {root}",
    },
    "app_new_template_label": {
        "ja": "テンプレート",
        "en": "Template",
    },
    "app_new_venv_label": {
        "ja": "venv（.venv）を作成する",
        "en": "Create a venv (.venv)",
    },
    "app_new_git_label": {
        "ja": "git init して最初のコミットまで作る",
        "en": "git init and make the initial commit",
    },
    "app_new_github_label": {
        "ja": "GitHubリポジトリ",
        "en": "GitHub repository",
    },
    "app_input_error_title": {
        "ja": "入力エラー",
        "en": "Input error",
    },
    "app_new_name_required": {
        "ja": "プロジェクト名を入力してください",
        "en": "Enter a project name",
    },
    "app_btn_create": {
        "ja": "作成する",
        "en": "Create",
    },
    "app_new_title": {
        "ja": "新規作成: {name}",
        "en": "Create: {name}",
    },
    "app_new_done": {
        "ja": "作成完了",
        "en": "Created",
    },
    "app_commit_title": {
        "ja": "コミット",
        "en": "Commit",
    },
    "app_commit_prompt": {
        "ja": "コミットメッセージ:",
        "en": "Commit message:",
    },
}
