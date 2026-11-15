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
def load_config() -> dict:
    cfg = {"projects_root": str(Path.home() / "Projects")}
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                           encoding="utf-8")


# ---------- 登録簿 ----------
def load_registry() -> list[dict]:
    if REGISTRY_FILE.exists():
        try:
            data = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return []


def save_registry(entries: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
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


# ---------- 新規作成 ----------
def create_project(name: str, root: str | Path, template: str = "python",
                   make_venv: bool = True, init_git: bool = True,
                   github: str = "none", log=print) -> dict:
    """新規プロジェクトを作って登録する。github: none/private/public"""
    name = name.strip()
    if not NAME_RE.match(name):
        raise ValueError("プロジェクト名は半角英数字・ハイフン・アンダースコアで、"
                         "英数字から始めてください（フォルダ名になります）")
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
