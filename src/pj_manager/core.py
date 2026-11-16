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
        return False, f"フォルダがありません: {cwd}"
    try:
        p = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out.strip()
    except FileNotFoundError:
        return False, f"コマンドが見つかりません: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "タイムアウトしました（600秒）"


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
    cfg = {"projects_root": str(Path.home() / "Projects")}
    if CONFIG_FILE.exists():
        data, corrupt = _parse_json_file(CONFIG_FILE)
        if not corrupt and isinstance(data, dict):
            cfg.update(data)
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
        raise ValueError(f"フォルダがありません: {p}")
    own = entries is None
    if own:
        entries = load_registry()
    for e in entries:
        if Path(e["path"]).resolve() == p:
            raise ValueError(f"すでに登録されています: {e['name']}")
        if e.get("name") == p.name:
            raise ValueError(
                f"同じ名前のプロジェクトがすでに登録されています: {p.name} "
                f"（{e['path']}）。フォルダ名を変えるか先に unregister してください")
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


def commit_all(path: str | Path, message: str) -> tuple[bool, str]:
    ok, out = git_op(path, "add", "-A")
    if not ok:
        return False, out
    return git_op(path, "commit", "-m", message)


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
        return False, "gh CLI が入っていません（https://cli.github.com/ からインストール）"
    ok, out = run_cmd(["gh", "auth", "status"])
    if not ok:
        return False, "gh にログインしていません。ターミナルで `gh auth login` を実行してください"
    return True, out


def github_create(path: str | Path, visibility: str = "private",
                  push: bool = True) -> tuple[bool, str]:
    """gh で GitHub リポジトリを作成して origin に接続する。"""
    p = Path(path)
    ok, msg = gh_available()
    if not ok:
        return False, msg
    if git_status(p)["remote"]:
        return False, "すでに origin が設定されています"
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
            f"Python {sys.version.split()[0]}（3.10 以上が必要です）")
    else:
        add("python", "ok", f"Python {sys.version.split()[0]}")

    # venv モジュール
    try:
        import venv  # noqa: F401
        add("venv", "ok", "venv モジュールが使えます")
    except ImportError:
        add("venv", "fail", "venv モジュールがありません")

    # git
    git = shutil.which("git")
    if git:
        ok, out = run_cmd(["git", "--version"])
        add("git", "ok", out.splitlines()[0] if ok and out else f"git ({git})")
    else:
        add("git", "warn", "git が見つかりません",
            "git を入れると git init / コミットなどの機能が使えます")

    # gh
    ok, _msg = gh_available()
    if ok:
        add("gh", "ok", "gh CLI にログイン済みです")
    elif shutil.which("gh"):
        add("gh", "warn", "gh CLI はありますがログインしていません",
            "ターミナルで `gh auth login` を実行してください")
    else:
        add("gh", "warn", "gh CLI が入っていません",
            "GitHub 機能を使う場合は https://cli.github.com/ からインストール")

    # projects_root
    cfg = load_config()
    root = Path(cfg.get("projects_root", "")).expanduser()
    if root.is_dir():
        add("projects_root", "ok", f"存在します: {root}")
    elif root.parent.is_dir() and os.access(root.parent, os.W_OK):
        add("projects_root", "ok",
            f"まだありません（初回作成時に作られます）: {root}")
    else:
        add("projects_root", "fail", f"作れません: {root}",
            "config set-root で書き込めるフォルダを指定してください")

    # data dir（書き込み可否を実際に試す）
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        probe = DATA_DIR / ".doctor-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        add("data_dir", "ok", f"書き込めます: {DATA_DIR}")
    except OSError as e:
        add("data_dir", "fail", f"書き込めません: {DATA_DIR} ({e})")

    # registry（壊れ・読み取れない件・同名重複・フォルダ無しの登録を検出）
    if REGISTRY_FILE.exists():
        entries, malformed, corrupt = _registry_state()
        if corrupt:
            add("registry", "fail",
                "projects.json が読めません（壊れている可能性があります）",
                "projects.json を削除すると空の登録簿から始められます"
                "（登録だけが消え、フォルダは残ります）")
        else:
            seen: dict[str, int] = {}
            for e in entries:
                seen[e["name"]] = seen.get(e["name"], 0) + 1
            dupes = sorted(n for n, c in seen.items() if c > 1)
            missing = [e["name"] for e in entries
                       if not Path(e["path"]).is_dir()]
            if malformed:
                add("registry", "warn",
                    f"{len(entries)} 件登録中・読み取れない登録が "
                    f"{malformed} 件あります",
                    "次に登録簿を保存するとき、読み取れない登録は "
                    "projects.json.bak-<日時> に退避されます")
            elif dupes:
                add("registry", "warn",
                    f"同じ名前の登録が重複しています: {', '.join(dupes)}",
                    "名前で区別できないため、片方を unregister してください")
            elif missing:
                add("registry", "warn",
                    f"{len(entries)} 件登録中・うちフォルダが無いもの: "
                    f"{', '.join(missing)}",
                    "存在しないフォルダの登録は unregister で外せます")
            elif entries:
                add("registry", "ok",
                    f"{len(entries)} 件登録中（フォルダは全て存在します）")
            else:
                add("registry", "ok", "登録はまだありません（空です）")
    else:
        add("registry", "ok", "まだありません（初回登録時に作られます）")

    # config（空ファイルは既定値扱い＝ok）
    if CONFIG_FILE.exists():
        data, corrupt = _parse_json_file(CONFIG_FILE)
        if corrupt or (data != "empty" and not isinstance(data, dict)):
            add("config", "warn", "config.json が読めません（既定値で動きます）",
                "config.json を削除すると既定値に戻ります")
        else:
            add("config", "ok", "config.json が読めます")
    else:
        add("config", "ok", "まだありません（既定値で動きます）")

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
        raise ValueError("プロジェクト名は半角英数字・ハイフン・アンダースコアで、"
                         "英数字から始めてください（フォルダ名になります）")
    if len(name.encode("utf-8")) > 255:
        raise ValueError("プロジェクト名が長すぎます（255バイト以内にしてください）")
    existing = find_entry(load_registry(), name)
    if existing is not None:
        raise ValueError(
            f"同じ名前のプロジェクトがすでに登録されています: {name} "
            f"（{existing['path']}）。別の名前にしてください")
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    if path.exists():
        raise ValueError(f"同じ名前のフォルダがすでにあります: {path}")

    path.mkdir(parents=True)
    log(f"フォルダを作成: {path}")
    (path / "README.md").write_text(README_TMPL.format(name=name), encoding="utf-8")
    if template == "python":
        (path / "main.py").write_text(MAIN_PY, encoding="utf-8")
        (path / ".gitignore").write_text(GITIGNORE_PYTHON, encoding="utf-8")
        (path / "requirements.txt").write_text("", encoding="utf-8")
        log("テンプレート（Python）を配置しました")

    if make_venv:
        log("venv を作成中…（少し時間がかかります）")
        ok, out = run_cmd([sys.executable, "-m", "venv", ".venv"], cwd=path)
        log("venv を作成しました" if ok else f"venv 作成に失敗: {out}")

    if init_git:
        if not shutil.which("git"):
            log("git が入っていないため、git init をスキップしました")
        else:
            ok, out = run_cmd(["git", "init", "-b", "main"], cwd=path)
            if not ok:  # 古いgit向けフォールバック
                run_cmd(["git", "init"], cwd=path)
                run_cmd(["git", "branch", "-M", "main"], cwd=path)
            log("git init しました")
            ok, out = commit_all(path, "Initial commit")
            if ok:
                log("最初のコミットを作成しました")
            else:
                log("最初のコミットはスキップしました。"
                    "（git のユーザー名/メール未設定などの場合は、設定後にコミットしてください）")

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
    log("プロジェクト一覧に登録しました")

    if github in ("private", "public"):
        ok, out = github_create(path, visibility=github, push=True)
        if ok:
            log(f"GitHub リポジトリを作成しました（{github}）")
        else:
            log(f"GitHub 作成に失敗: {out}")
            log("プロジェクト自体はできています。後から一覧のボタンでも作成できます")
    return entry
