#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pj_manager/core.py — 総合PJ管理システムのコアロジック（GUIなしで使える部分）

- プロジェクト登録簿（projects.json）の読み書き
- 新規プロジェクト作成（フォルダ・venv・git init・GitHub作成まで）
- 既存プロジェクトの登録
- git の状態取得と基本操作（commit / push / pull / log）
- GitHub 操作（gh CLI 経由）

データファイル（projects.json / config.json）はリポジトリのルート
（run.bat と同じフォルダ）に置く。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pj_manager import i18n


def _t(key: str, **kwargs) -> str:
    """このモジュールの表示文字列。言語は config.json の `language`。

    CONFIG_FILE はテストで差し替えられるので、毎回読み直す。
    """
    return i18n.t(key, lang=i18n.get_language(CONFIG_FILE), **kwargs)

# データ置き場: 環境変数 PJ_MANAGER_DATA_DIR があればそこ、
# なければ src/pj_manager/core.py から見て2つ上（リポジトリのルート）。
# エージェントやテストがサンドボックスへ差し替えられるようにするための口。
_env_data = os.environ.get("PJ_MANAGER_DATA_DIR")
DATA_DIR = (Path(_env_data).expanduser() if _env_data
            else Path(__file__).resolve().parents[2])
REGISTRY_FILE = DATA_DIR / "projects.json"
CONFIG_FILE = DATA_DIR / "config.json"

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

GITIGNORE_PYTHON = """\
.venv/
__pycache__/
*.pyc
.env
.vscode/
dist/
build/
*.egg-info/
"""

MAIN_PY = '''\
"""エントリーポイント。ここから書き始めてください。"""


def main() -> None:
    print("Hello, project!")


if __name__ == "__main__":
    main()
'''

README_TMPL = """\
# {name}

（プロジェクトの説明をここに書く）

## 動かし方

```
.venv\\Scripts\\activate
python main.py
```
"""


# ---------- 汎用 ----------
def run_cmd(cmd: list[str], cwd: Path | None = None) -> tuple[bool, str]:
    """コマンドを実行して (成功か, 出力) を返す。例外は投げない。"""
    if cwd is not None and not Path(cwd).is_dir():
        # subprocess は存在しない cwd で FileNotFoundError を出すが、
        # それを「コマンドが見つかりません」と誤訳しないための先回り。
        return False, _t("folder_missing", path=cwd)
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out.strip()
    except FileNotFoundError:
        return False, _t("command_not_found", cmd=cmd[0])
    except subprocess.TimeoutExpired:
        return False, _t("timeout")


def has_venv(path: Path) -> bool:
    return (path / ".venv" / "Scripts" / "activate.bat").exists() or \
           (path / ".venv" / "bin" / "activate").exists()


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


# ---------- 設定 ----------
def _parse_json_file(path: Path):
    """JSON ファイルを読む。空ファイルは空の値として扱う。

    戻り値: (parsed, corrupt)。
    parsed が None なら corrupt（読めない・壊れている）。
    空ファイル / 空白だけのファイルは空の値（[] / {} を呼出側が決める）。
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, True
    if not text.strip():
        return "empty", False
    try:
        return json.loads(text), False
    except json.JSONDecodeError:
        return None, True


def load_config() -> dict:
    cfg = {"projects_root": str(Path.home() / "Projects"),
           "language": i18n.DEFAULT_LANGUAGE}
    if CONFIG_FILE.exists():
        data, corrupt = _parse_json_file(CONFIG_FILE)
        if not corrupt and isinstance(data, dict):
            cfg.update(data)
    cfg["language"] = i18n.normalize_language(cfg.get("language"))
    return cfg


def save_config(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                           encoding="utf-8")


# ---------- 登録簿 ----------
def _is_valid_entry(e) -> bool:
    """登録簿の1件として使える形か（dict で name / path が空でない文字列）。"""
    return (isinstance(e, dict)
            and isinstance(e.get("name"), str) and bool(e["name"])
            and isinstance(e.get("path"), str) and bool(e["path"]))


def _registry_state() -> tuple[list[dict], int, bool]:
    """(有効な登録一覧, 読み取れない件数, 壊れているか) を返す。

    空ファイルは空の登録簿（壊れではない）。配列でない中身・JSON
    構文エラーは「壊れている」。読み取れない件（dict でない・
    name/path が無い等）は一覧から外す。外された件は doctor が
    warn として知らせる。
    """
    if not REGISTRY_FILE.exists():
        return [], 0, False
    data, corrupt = _parse_json_file(REGISTRY_FILE)
    if corrupt:
        return [], 0, True
    if data == "empty":
        return [], 0, False
    if not isinstance(data, list):
        return [], 0, True
    valid = [e for e in data if _is_valid_entry(e)]
    return valid, len(data) - len(valid), False


def load_registry() -> list[dict]:
    """有効な登録だけを返す。壊れた登録簿は空扱い（doctor が fail を出す）。

    読み取れない件があっても他のコマンドが落ちないようにする。
    上書きで消えてしまう前に _backup_registry_if_dirty() が中身を退避する。
    """
    entries, _malformed, _corrupt = _registry_state()
    return entries


def _backup_registry_if_dirty() -> str | None:
    """登録簿ファイルが壊れている／読み取れない件を含む場合、

    上書きで失われる前に projects.json.bak-<日時> へ退避する。
    退避したらそのパス、不要なら None を返す。
    """
    _entries, malformed, corrupt = _registry_state()
    if not corrupt and malformed == 0:
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = REGISTRY_FILE.with_name(f"projects.json.bak-{stamp}")
    try:
        shutil.copyfile(REGISTRY_FILE, backup)
        return str(backup)
    except OSError:
        return None


def save_registry(entries: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _backup_registry_if_dirty()
    REGISTRY_FILE.write_text(json.dumps(entries, ensure_ascii=False, indent=2),
                             encoding="utf-8")


def find_entry(entries: list[dict], name: str) -> dict | None:
    for e in entries:
        if e.get("name") == name:
            return e
    return None


def register_existing(path: str | Path, entries: list[dict] | None = None) -> dict:
    """既存フォルダを登録する。entries を渡すとそこへ追加して保存する。"""
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        raise ValueError(_t("folder_missing", path=p))
    own = entries is None
    if own:
        entries = load_registry()
    for e in entries:
        if Path(e["path"]).resolve() == p:
            raise ValueError(_t("already_registered", name=e["name"]))
        if e.get("name") == p.name:
            raise ValueError(_t("duplicate_name_register",
                                name=p.name, path=e["path"]))
    entry = {
        "name": p.name,
        "path": str(p),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "origin": "existing",
    }
    entries.append(entry)
    entries.sort(key=lambda x: x["name"].lower())
    save_registry(entries)
    return entry


def unregister(name: str, entries: list[dict] | None = None) -> bool:
    """登録だけ外す（フォルダ自体は消さない）。"""
    own = entries is None
    if own:
        entries = load_registry()
    before = len(entries)
    entries[:] = [e for e in entries if e.get("name") != name]
    if len(entries) != before:
        save_registry(entries)
        return True
    return False


# ---------- git ----------
def git_status(path: str | Path) -> dict:
    """git の状態を辞書で返す（git管理外なら is_git=False）。"""
    p = Path(path)
    st: dict = {"is_git": is_git_repo(p), "branch": "", "dirty": 0,
                "ahead": 0, "behind": 0, "remote": "", "last_commit": ""}
    if not st["is_git"]:
        return st
    ok, out = run_cmd(["git", "status", "--porcelain", "--branch"], cwd=p)
    if ok and out:
        lines = out.splitlines()
        head = lines[0] if lines and lines[0].startswith("##") else ""
        m = re.match(r"## (?:No commits yet on )?([^. \[]+)", head)
        if m:
            st["branch"] = m.group(1)
        ma = re.search(r"ahead (\d+)", head)
        mb = re.search(r"behind (\d+)", head)
        if ma:
            st["ahead"] = int(ma.group(1))
        if mb:
            st["behind"] = int(mb.group(1))
        st["dirty"] = sum(1 for ln in lines if not ln.startswith("##"))
    ok, out = run_cmd(["git", "remote", "get-url", "origin"], cwd=p)
    if ok:
        st["remote"] = out
    ok, out = run_cmd(["git", "log", "-1", "--pretty=%h %ad %s", "--date=short"], cwd=p)
    if ok:
        st["last_commit"] = out
    return st


def git_op(path: str | Path, *args: str) -> tuple[bool, str]:
    return run_cmd(["git", *args], cwd=Path(path))


def upstream_state(path: str | Path) -> str:
    """push / pull の前提（リモートと上流ブランチ）の状態を返す。

    "ok" / "no-remote" / "no-upstream" のいずれか。判定は git の
    終了コードだけで行い、git の文言（ロケールで変わる）には依存しない。
    """
    ok, out = run_cmd(["git", "remote"], cwd=Path(path))
    if not ok or not out.strip():
        return "no-remote"
    ok, _out = run_cmd(["git", "rev-parse", "--abbrev-ref",
                        "--symbolic-full-name", "@{u}"], cwd=Path(path))
    return "ok" if ok else "no-upstream"


def git_push_pull(path: str | Path, op: str) -> tuple[bool, str]:
    """git push / pull。リモート未設定・上流ブランチ未設定のときは
    git の生の英語エラーではなく、次に何をすればよいか分かる
    日英の文言で失敗する（セッション15〜17の変更なしコミット・
    コミット0件の log と同じ考え方）。それ以外の本物の失敗
    （到達できないリモート、認証エラーなど）は従来どおり git の
    出力をそのまま返す。コミットがまだ無いリポジトリは push/pull
    の前提以前の問題なので、git の出力をそのまま返す。
    """
    p = Path(path)
    ok, out = git_op(p, op)
    if ok:
        return True, out
    if shutil.which("git") and has_commits(p):
        state = upstream_state(p)
        if state == "no-remote":
            return False, _t("cli_no_remote")
        if state == "no-upstream":
            branch = git_status(p).get("branch") or "main"
            if op == "push":
                return False, _t("cli_no_upstream_push", branch=branch)
            return False, _t("cli_no_upstream_pull", branch=branch)
    return False, out


def has_commits(path: str | Path) -> bool:
    """HEAD が指すコミットがあるか。まだ1件も無い空のリポジトリは False。

    判定は `git rev-parse --verify HEAD` の終了コードだけで行い、
    git の文言（ロケールで変わる）には依存しない。
    """
    ok, _out = run_cmd(["git", "rev-parse", "--verify", "HEAD"],
                       cwd=Path(path))
    return ok


def git_identity_configured(path: str | Path) -> bool:
    """コミットに使う user.name / user.email が設定済みか（有効な設定）。

    `git config user.name` / `user.email` はローカル・グローバル・
    システムの設定を合わせた有効値を返し、未設定なら終了コード 1
    になる。判定は終了コードと空かどうかだけで行い、git の文言
    （ロケールで変わる）には依存しない。git が無い環境では False。
    `git commit` は設定の代わりに GIT_AUTHOR_NAME / GIT_AUTHOR_EMAIL
    （committer 側は GIT_COMMITTER_NAME / GIT_COMMITTER_EMAIL）も
    見るので、環境変数で補われている場合も設定済みとみなす。
    """
    if not shutil.which("git"):
        return False

    def _config(key: str) -> str:
        ok, out = run_cmd(["git", "config", key], cwd=Path(path))
        return out.strip() if ok and out.strip() else ""

    cfg_name = _config("user.name")
    cfg_email = _config("user.email")
    author_name = os.environ.get("GIT_AUTHOR_NAME") or cfg_name
    author_email = os.environ.get("GIT_AUTHOR_EMAIL") or cfg_email
    committer_name = os.environ.get("GIT_COMMITTER_NAME") or cfg_name
    committer_email = os.environ.get("GIT_COMMITTER_EMAIL") or cfg_email
    return bool(author_name and author_email
                and committer_name and committer_email)


def commit_all(path: str | Path, message: str) -> tuple[bool, str]:
    """git add -A && git commit -m message。

    変更が無くてコミットするものが無い場合は、git は終了コード 1 で
    "nothing to commit" を返すが、望む最終状態（全部コミット済み）は
    既に満たされているので失敗ではなく成功として扱う。失敗したのに
    ツリーがクリーンな場合だけがこれに当たる（未設定のユーザー名や
    フック失敗など、ステージ済みの変更が残る失敗は従来どおり失敗）。
    git の文言はロケールで変わるので、判定は git_status の dirty 数
    で行い、文言には依存しない。

    user.name / user.email が未設定のままコミットしようとすると git は
    終了コード 128 で英語の "Author identity unknown" を返すが、
    次の一手は決まっている（`git config --global user.name` /
    `user.email` で設定する）ので、コミットを試す前に
    git_identity_configured() で検出して日英の親切な文言で失敗する。
    変更が無い場合は identity が無くても成功扱い（コミットを作る
    必要が無いため）。

    コミットメッセージが空（空文字・空白だけ）の場合は、git に渡す
    前に日英の親切な文言で失敗する。git は終了コード 1 で英語の
    "Aborting commit due to empty commit message." を返すだけだが、
    次の一手は決まっている（-m でメッセージを指定する）ので、
    セッション15〜19と同じ考え方。`git add -A` より前に弾くので、
    失敗しても変更がステージされることはない。
    """
    if not message or not message.strip():
        return False, _t("core_empty_commit_message")
    ok, out = git_op(path, "add", "-A")
    if not ok:
        return False, out
    if git_status(path)["dirty"] == 0:
        return True, _t("core_nothing_to_commit")
    if not git_identity_configured(path):
        return False, _t("core_no_git_identity")
    ok, out = git_op(path, "commit", "-m", message)
    if ok:
        return True, out
    if git_status(path)["dirty"] == 0:
        return True, _t("core_nothing_to_commit")
    return False, out


# ---------- 横断ヘルスチェック（check） ----------
def project_health(entry: dict) -> dict:
    """1件のプロジェクトの健全性を辞書で返す。

    state は "ok" / "attention" / "missing" のいずれか。
    - missing: 登録されたフォルダが無い（doctor の warn 相当だが、
      check では全体の ok を False にする）。
    - attention: フォルダはあるが、dirty / ahead / behind / venv無し /
      git管理外のいずれかがある。
    - ok: それ以外（クリーン・同期済み・venv 有り）。
    issues は気になる点の短いタグ一覧（人間向けの目安）。
    """
    path = Path(entry["path"])
    info = dict(entry)
    info["exists"] = path.is_dir()
    info["has_venv"] = has_venv(path) if info["exists"] else False
    git = git_status(path) if info["exists"] else {
        "is_git": False, "branch": "", "dirty": 0,
        "ahead": 0, "behind": 0, "remote": "", "last_commit": ""}
    info["git"] = git
    issues: list[str] = []
    if not info["exists"]:
        info["state"] = "missing"
        issues.append("missing")
    else:
        if not git["is_git"]:
            issues.append("not-git")
        else:
            if git["dirty"]:
                issues.append(f"dirty:{git['dirty']}")
            if git["ahead"]:
                issues.append(f"ahead:{git['ahead']}")
            if git["behind"]:
                issues.append(f"behind:{git['behind']}")
        if not info["has_venv"]:
            issues.append("no-venv")
        info["state"] = "attention" if issues else "ok"
    info["issues"] = issues
    return info


def check_all() -> dict:
    """登録中の全プロジェクトの健全性を一括で返す（check コマンドの中身）。

    ok はフォルダが無い登録（missing）が1件も無いこと。
    dirty / ahead / behind / venv無し / git管理外は attention であって
    fail ではない（doctor と同じ考え方）。summary は件数の集計。
    """
    projects = [project_health(e) for e in load_registry()]
    summary = {"total": len(projects), "ok": 0, "attention": 0,
               "missing": 0, "dirty": 0, "ahead": 0, "behind": 0,
               "no_venv": 0, "not_git": 0}
    for p in projects:
        summary[p["state"]] += 1
        git = p.get("git", {})
        if p["exists"]:
            if git.get("dirty"):
                summary["dirty"] += 1
            if git.get("ahead"):
                summary["ahead"] += 1
            if git.get("behind"):
                summary["behind"] += 1
            if not p["has_venv"]:
                summary["no_venv"] += 1
            if not git.get("is_git"):
                summary["not_git"] += 1
    return {"ok": summary["missing"] == 0,
            "projects": projects, "summary": summary}


# ---------- GitHub（gh CLI） ----------
def gh_available() -> tuple[bool, str]:
    if not shutil.which("gh"):
        return False, _t("gh_not_installed")
    ok, out = run_cmd(["gh", "auth", "status"])
    if not ok:
        return False, _t("gh_not_logged_in")
    return True, out


def github_create(path: str | Path, visibility: str = "private",
                  push: bool = True) -> tuple[bool, str]:
    """gh で GitHub リポジトリを作成して origin に接続する。"""
    p = Path(path)
    ok, msg = gh_available()
    if not ok:
        return False, msg
    if git_status(p)["remote"]:
        return False, _t("origin_already_set")
    cmd = ["gh", "repo", "create", p.name, f"--{visibility}",
           "--source", str(p), "--remote", "origin"]
    if push:
        cmd.append("--push")
    return run_cmd(cmd, cwd=p)


def github_web_url(path: str | Path) -> str:
    remote = git_status(path)["remote"]
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    if m:
        return f"https://github.com/{m.group(1)}"
    return ""


# ---------- 健全性チェック（doctor） ----------
def doctor() -> dict:
    """環境の健全性を点検する（doctor コマンドの中身）。

    checks は [{name, level, detail, hint?}] のリスト。
    level は "ok" / "warn" / "fail"。全体の status は fail が
    1つでもあれば "fail"、なければ warn があれば "warn"、それ以外 "ok"。
    ok は fail が無いこと（warn だけなら終了コード 0）。
    デスクトップUIやエージェントの起動時チェック用。
    """
    checks: list[dict] = []

    def add(name: str, level: str, detail: str, hint: str = "") -> None:
        c: dict = {"name": name, "level": level, "detail": detail}
        if hint:
            c["hint"] = hint
        checks.append(c)

    # Python
    ver = sys.version_info
    if ver < (3, 10):
        add("python", "fail",
            _t("doctor_python_old", version=sys.version.split()[0]))
    else:
        add("python", "ok", f"Python {sys.version.split()[0]}")

    # venv モジュール
    try:
        import venv  # noqa: F401
        add("venv", "ok", _t("doctor_venv_ok"))
    except ImportError:
        add("venv", "fail", _t("doctor_venv_missing"))

    # git
    git = shutil.which("git")
    if git:
        ok, out = run_cmd(["git", "--version"])
        add("git", "ok", out.splitlines()[0] if ok and out else f"git ({git})")
    else:
        add("git", "warn", _t("doctor_git_missing"),
            _t("doctor_git_missing_hint"))

    # git identity（コミットに使う user.name / user.email）。
    # doctor は環境の点検なので、リポジトリごとの設定ではなく
    # グローバル設定を見る。リポジトリごとに設定している場合は
    # コミット自体は動くので、warn のヒントにその旨を書く。
    # 判定は `git config --global` の終了コードだけで行う。
    if git:
        ok_name, out_name = run_cmd(["git", "config", "--global", "user.name"])
        ok_email, out_email = run_cmd(
            ["git", "config", "--global", "user.email"])
        if ok_name and out_name.strip() and ok_email and out_email.strip():
            add("git_identity", "ok", _t("doctor_identity_ok"))
        else:
            add("git_identity", "warn", _t("doctor_identity_missing"),
                _t("doctor_identity_missing_hint"))

    # gh
    ok, _msg = gh_available()
    if ok:
        add("gh", "ok", _t("doctor_gh_ok"))
    elif shutil.which("gh"):
        add("gh", "warn", _t("doctor_gh_not_logged_in"),
            _t("doctor_gh_not_logged_in_hint"))
    else:
        add("gh", "warn", _t("doctor_gh_missing"),
            _t("doctor_gh_missing_hint"))

    # projects_root
    cfg = load_config()
    root = Path(cfg.get("projects_root", "")).expanduser()
    if root.exists() and not root.is_dir():
        # ファイルが置いてある場所にはフォルダを作れない。create は
        # 親切な文言で失敗する（v0.24.0）のに、doctor が「初回作成時に
        # 作られます」と ok を出すのは矛盾するので、ここでは fail にする。
        add("projects_root", "fail",
            _t("doctor_root_is_file", path=root),
            _t("doctor_root_is_file_hint"))
    elif root.is_dir():
        add("projects_root", "ok", _t("doctor_root_ok", path=root))
    elif root.parent.is_dir() and os.access(root.parent, os.W_OK):
        add("projects_root", "ok",
            _t("doctor_root_will_create", path=root))
    else:
        add("projects_root", "fail", _t("doctor_root_fail", path=root),
            _t("doctor_root_fail_hint"))

    # data dir（書き込み可否を実際に試す）
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".doctor-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        add("data_dir", "ok", _t("doctor_data_ok", path=DATA_DIR))
    except OSError as e:
        add("data_dir", "fail", _t("doctor_data_fail", path=DATA_DIR, error=e))

    # registry（壊れ・読み取れない件・同名重複・フォルダ無しの登録を検出）
    if REGISTRY_FILE.exists():
        entries, malformed, corrupt = _registry_state()
        if corrupt:
            add("registry", "fail",
                _t("doctor_registry_corrupt"),
                _t("doctor_registry_corrupt_hint"))
        else:
            seen: dict[str, int] = {}
            for e in entries:
                seen[e["name"]] = seen.get(e["name"], 0) + 1
            dupes = sorted(n for n, c in seen.items() if c > 1)
            missing = [e["name"] for e in entries
                       if not Path(e["path"]).is_dir()]
            if malformed:
                add("registry", "warn",
                    _t("doctor_registry_malformed",
                       count=len(entries), malformed=malformed),
                    _t("doctor_registry_malformed_hint"))
            elif dupes:
                add("registry", "warn",
                    _t("doctor_registry_dupes", names=", ".join(dupes)),
                    _t("doctor_registry_dupes_hint"))
            elif missing:
                add("registry", "warn",
                    _t("doctor_registry_missing",
                       count=len(entries), names=", ".join(missing)),
                    _t("doctor_registry_missing_hint"))
            elif entries:
                add("registry", "ok",
                    _t("doctor_registry_ok", count=len(entries)))
            else:
                add("registry", "ok", _t("doctor_registry_empty"))
    else:
        add("registry", "ok", _t("doctor_registry_absent"))

    # config（空ファイルは既定値扱い＝ok）
    if CONFIG_FILE.exists():
        data, corrupt = _parse_json_file(CONFIG_FILE)
        if corrupt or (data != "empty" and not isinstance(data, dict)):
            add("config", "warn", _t("doctor_config_unreadable"),
                _t("doctor_config_unreadable_hint"))
        else:
            add("config", "ok", _t("doctor_config_ok"))
    else:
        add("config", "ok", _t("doctor_config_absent"))

    levels = [c["level"] for c in checks]
    status = "fail" if "fail" in levels else (
        "warn" if "warn" in levels else "ok")
    summary = {"ok": 0, "warn": 0, "fail": 0}
    for lv in levels:
        summary[lv] += 1
    return {"ok": status != "fail", "status": status,
            "checks": checks, "summary": summary}


# ---------- 新規作成 ----------
def create_project(name: str, root: str | Path, template: str = "python",
                   make_venv: bool = True, init_git: bool = True,
                   github: str = "none", log=print) -> dict:
    """新規プロジェクトを作って登録する。github: none/private/public"""
    name = name.strip()
    if not NAME_RE.match(name):
        raise ValueError(_t("invalid_name"))
    if len(name.encode("utf-8")) > 255:
        raise ValueError(_t("name_too_long"))
    existing = find_entry(load_registry(), name)
    if existing is not None:
        raise ValueError(_t("duplicate_name_create",
                            name=name, path=existing["path"]))
    root = Path(root).expanduser()
    # --root がファイルそのもの、または途中の要素がファイルだと
    # root.mkdir() が FileExistsError / NotADirectoryError という
    # Python の生の例外で失敗する。呼び出し側の指定ミスなので、
    # git に渡す前に日英の親切な文言で失敗させる（log -n の不正な
    # 件数や空のコミットメッセージと同じ考え方）。
    if root.exists() and not root.is_dir():
        raise ValueError(_t("root_not_a_folder", path=root))
    try:
        root.mkdir(parents=True, exist_ok=True)
    except NotADirectoryError:
        raise ValueError(_t("root_parent_is_file", path=root))
    path = root / name
    if path.exists():
        if path.is_dir():
            raise ValueError(_t("folder_exists", path=path))
        raise ValueError(_t("file_exists", path=path))

    path.mkdir(parents=True)
    log(_t("log_folder_created", path=path))
    (path / "README.md").write_text(README_TMPL.format(name=name), encoding="utf-8")
    if template == "python":
        (path / "main.py").write_text(MAIN_PY, encoding="utf-8")
        (path / ".gitignore").write_text(GITIGNORE_PYTHON, encoding="utf-8")
        (path / "requirements.txt").write_text("", encoding="utf-8")
        log(_t("log_template_placed"))

    if make_venv:
        log(_t("log_venv_creating"))
        ok, out = run_cmd([sys.executable, "-m", "venv", ".venv"], cwd=path)
        log(_t("log_venv_created") if ok else _t("log_venv_failed", out=out))

    if init_git:
        if not shutil.which("git"):
            log(_t("log_git_skip_no_git"))
        else:
            ok, out = run_cmd(["git", "init", "-b", "main"], cwd=path)
            if not ok:  # 古いgit向けフォールバック
                run_cmd(["git", "init"], cwd=path)
                run_cmd(["git", "branch", "-M", "main"], cwd=path)
            log(_t("log_git_init"))
            ok, out = commit_all(path, "Initial commit")
            if ok:
                log(_t("log_first_commit"))
            else:
                log(_t("log_first_commit_skip"))

    entry = {
        "name": name,
        "path": str(path.resolve()),
        "created_at": datetime.now().strftime("%Y-%m-%d"),
        "origin": "created",
    }
    entries = load_registry()
    entries.append(entry)
    entries.sort(key=lambda x: x["name"].lower())
    save_registry(entries)
    log(_t("log_registered"))

    if github in ("private", "public"):
        ok, out = github_create(path, visibility=github, push=True)
        if ok:
            log(_t("log_github_created", visibility=github))
        else:
            log(_t("log_github_failed", out=out))
            log(_t("log_github_project_ok"))
    return entry
