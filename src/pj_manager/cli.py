#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pj_manager/cli.py — CLI for scripts and AI agents.

Drives the same pj_manager.core as the GUI. Design rules for automation:

- `--json` makes stdout a single machine-readable JSON object.
- Exit code 0 = success, 1 = failure (failures are JSON too, with --json).
- No interactive prompts, ever.
- Data files (projects.json / config.json) live in the repository root,
  or in the folder named by the PJ_MANAGER_DATA_DIR environment variable.

Examples:
  python -m pj_manager.cli list --json
  python -m pj_manager.cli create my-app --json
  python -m pj_manager.cli status my-app --json
  python -m pj_manager.cli init my-app --json
  python -m pj_manager.cli doctor --json
  python -m pj_manager.cli check --json
  python -m pj_manager.cli config show --json
  python -m pj_manager.cli config set-root DIR --json
  python -m pj_manager.cli config set-language ja|en --json

Display language: config.json `language` ("ja" default / "en").
Human-readable output and error messages follow it; --json output
(keys and values) does not change with the language.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pj_manager import core, i18n

# 表示言語。main() が config.json から決めて全ハンドラで使う。
_LANG = i18n.DEFAULT_LANGUAGE


def _t(key: str, **kwargs) -> str:
    return i18n.t(key, lang=_LANG, **kwargs)


def _out(obj: dict, as_json: bool, human: str | None = None) -> int:
    if as_json or human is None:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(human)
    return 0


def _fail(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"ok": False, "error": message},
                         ensure_ascii=False, indent=2))
    else:
        print(f"error: {message}", file=sys.stderr)
    return 1


def _resolve(target: str) -> Path:
    """A target is a registered project name or a folder path."""
    p = Path(target).expanduser()
    if p.is_dir():
        return p.resolve()
    entry = core.find_entry(core.load_registry(), target)
    if entry:
        return Path(entry["path"])
    raise ValueError(_t("cli_project_not_found", target=target))


def _project_info(entry: dict) -> dict:
    path = Path(entry["path"])
    info = dict(entry)
    info["exists"] = path.is_dir()
    info["has_venv"] = core.has_venv(path) if info["exists"] else False
    if info["exists"]:
        info["git"] = core.git_status(path)
    return info


def cmd_list(args) -> int:
    infos = [_project_info(e) for e in core.load_registry()]
    human = "\n".join(
        f"{i['name']:<24} {i['path']}  "
        f"[{'venv' if i['has_venv'] else 'no-venv'}"
        f"{' git:' + i['git']['branch'] if i.get('git', {}).get('is_git') else ''}]"
        f"{' [' + _t('cli_list_missing') + ']' if not i['exists'] else ''}"
        for i in infos
    ) or _t("cli_no_projects")
    return _out({"ok": True, "projects": infos}, args.json, human)


def cmd_create(args) -> int:
    logs: list[str] = []
    root = args.root or core.load_config().get("projects_root")
    entry = core.create_project(
        args.name, root,
        make_venv=not args.no_venv, init_git=not args.no_git,
        github=args.github, log=logs.append,
    )
    return _out(
        {"ok": True, "project": _project_info(entry), "log": logs},
        args.json,
        _t("cli_created", path=entry["path"]),
    )


def cmd_register(args) -> int:
    entry = core.register_existing(args.path)
    return _out({"ok": True, "project": _project_info(entry)}, args.json,
                _t("cli_registered", name=entry["name"], path=entry["path"]))


def cmd_unregister(args) -> int:
    if not core.unregister(args.name):
        return _fail(_t("cli_no_registration", name=args.name), args.json)
    return _out({"ok": True, "unregistered": args.name}, args.json,
                _t("cli_unregistered", name=args.name))


def cmd_status(args) -> int:
    path = _resolve(args.target)
    # フォルダが無い登録（ghost）は「git 管理外」ではなくフォルダ無しとして
    # 失敗させる。check と同じ考え方で、JSON は {"ok": false, "error": ...}。
    err = _require_dir(path)
    if err:
        return _fail(err, args.json)
    entry = core.find_entry(core.load_registry(), path.name)
    base = entry or {"name": path.name, "path": str(path)}
    info = _project_info({**base, "path": str(path)})
    git = info.get("git", {})
    human = (
        f"{info['name']}: {info['path']}\n"
        "  " + _t("cli_status_venv", value="yes" if info["has_venv"] else "no") + "\n"
        + ("  " + _t("cli_status_git", branch=git.get("branch", ""),
                      dirty=git.get("dirty", 0), ahead=git.get("ahead", 0),
                      behind=git.get("behind", 0)) + "\n"
           + "  " + _t("cli_status_last", last=git.get("last_commit", ""))
           if git.get("is_git") else "  " + _t("cli_status_not_git"))
    )
    return _out({"ok": True, "project": info}, args.json, human)


def _require_dir(path: Path) -> str | None:
    if not path.is_dir():
        return _t("folder_missing", path=path)
    return None


def _require_git_repo(path: Path) -> str | None:
    err = _require_dir(path)
    if err:
        return err
    if not core.is_git_repo(path):
        return _t("cli_not_git_repo", path=path)
    return None


def cmd_commit(args) -> int:
    path = _resolve(args.target)
    err = _require_git_repo(path)
    if err:
        return _fail(err, args.json)
    ok, out = core.commit_all(path, args.message)
    if not ok:
        return _fail(out or _t("cli_commit_failed"), args.json)
    return _out({"ok": True, "output": out}, args.json, out)


def cmd_git_op(op: str):
    def run(args) -> int:
        path = _resolve(args.target)
        err = _require_git_repo(path)
        if err:
            return _fail(err, args.json)
        ok, out = core.git_op(path, op)
        if not ok:
            return _fail(out or _t("cli_git_op_failed", op=op), args.json)
        return _out({"ok": True, "output": out}, args.json, out)
    return run


def cmd_log(args) -> int:
    path = _resolve(args.target)
    err = _require_git_repo(path)
    if err:
        return _fail(err, args.json)
    ok, out = core.git_op(
        path, "log", f"-{args.n}", "--pretty=%h %ad %s", "--date=short")
    if not ok:
        return _fail(out or _t("cli_log_failed"), args.json)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return _out({"ok": True, "log": lines}, args.json, "\n".join(lines))


def cmd_init(args) -> int:
    path = _resolve(args.target)
    err = _require_dir(path)
    if err:
        return _fail(err, args.json)
    if core.is_git_repo(path):
        return _out({"ok": True, "output": _t("cli_already_git")},
                    args.json, _t("cli_already_git"))
    ok, out = core.git_op(path, "init", "-b", "main")
    if not ok:
        return _fail(out or _t("cli_init_failed"), args.json)
    return _out({"ok": True, "output": out}, args.json, out)


def cmd_check(args) -> int:
    result = core.check_all()
    lines = []
    for p in result["projects"]:
        git = p.get("git", {})
        if not p["exists"]:
            git_s = "missing"
        elif not git.get("is_git"):
            git_s = "not-git"
        else:
            git_s = (f"{git.get('branch', '')} dirty={git.get('dirty', 0)} "
                     f"ahead={git.get('ahead', 0)} "
                     f"behind={git.get('behind', 0)}")
        issues = f" ({', '.join(p['issues'])})" if p["issues"] else ""
        lines.append(f"{p['name']:<24} [{p['state']}] "
                     f"{'venv' if p['has_venv'] else 'no-venv'} "
                     f"{git_s}{issues}")
    s = result["summary"]
    lines.append(_t("cli_check_summary", total=s["total"], ok=s["ok"],
                    attention=s["attention"], missing=s["missing"]))
    _out(result, args.json,
         "\n".join(lines) if lines else _t("cli_no_projects"))
    return 0 if result["ok"] else 1


def cmd_doctor(args) -> int:
    result = core.doctor()
    marks = {"ok": "✓", "warn": "!", "fail": "✗"}
    lines = []
    for c in result["checks"]:
        line = f"{marks[c['level']]} {c['name']}: {c['detail']}"
        if c.get("hint"):
            line += f" — {c['hint']}"
        lines.append(line)
    s = result["summary"]
    lines.append(_t("cli_doctor_status", status=result["status"],
                    ok=s["ok"], warn=s["warn"], fail=s["fail"]))
    _out({"ok": result["ok"], "status": result["status"],
          "checks": result["checks"], "summary": s},
         args.json, "\n".join(lines))
    return 0 if result["ok"] else 1


def cmd_config(args) -> int:
    cfg = core.load_config()
    if args.action == "show":
        return _out({"ok": True, "config": cfg}, args.json,
                    "\n".join(f"{k}: {v}" for k, v in cfg.items()))
    if args.action == "set-root":
        cfg["projects_root"] = str(Path(args.value).expanduser())
        core.save_config(cfg)
        return _out({"ok": True, "config": cfg}, args.json,
                    _t("cli_config_root_set", value=cfg["projects_root"]))
    if args.action == "set-language":
        value = (args.value or "").strip().lower()
        if value not in i18n.LANGUAGES:
            return _fail(_t("cli_invalid_language", value=args.value or ""),
                         args.json)
        cfg["language"] = value
        core.save_config(cfg)
        return _out({"ok": True, "config": cfg}, args.json,
                    _t("cli_set_language", value=cfg["language"]))
    return _fail(_t("cli_unknown_config_action", action=args.action), args.json)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pj-manager",
        description="Manage Python projects (GUI core, CLI face)",
        epilog="Global option: --json (machine-readable output; "
               "accepted in any position)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list registered projects")

    c = sub.add_parser("create", help="create a new project")
    c.add_argument("name")
    c.add_argument("--root", help="parent folder (default: config projects_root)")
    c.add_argument("--no-venv", action="store_true")
    c.add_argument("--no-git", action="store_true")
    c.add_argument("--github", choices=["none", "private", "public"],
                   default="none")

    r = sub.add_parser("register", help="register an existing folder")
    r.add_argument("path")

    u = sub.add_parser("unregister", help="unregister (folder is kept)")
    u.add_argument("name")

    s = sub.add_parser("status", help="show one project's status")
    s.add_argument("target", help="project name or folder path")

    cm = sub.add_parser("commit", help="git add -A && commit")
    cm.add_argument("target")
    cm.add_argument("-m", "--message", required=True)

    ini = sub.add_parser("init", help="git init (branch: main)")
    ini.add_argument("target")

    for op in ("push", "pull"):
        g = sub.add_parser(op, help=f"git {op}")
        g.add_argument("target")

    lg = sub.add_parser("log", help="recent git log")
    lg.add_argument("target")
    lg.add_argument("-n", type=int, default=10)

    cf = sub.add_parser("config", help="show or change settings")
    cf.add_argument("action", choices=["show", "set-root", "set-language"])
    cf.add_argument("value", nargs="?",
                    help="folder path for set-root, ja|en for set-language")

    sub.add_parser("doctor", help="check environment health "
                   "(python / git / gh / paths / registry)")

    sub.add_parser("check", help="health of all registered projects "
                   "(dirty / ahead / behind / venv) as one JSON")
    return p


HANDLERS = {
    "list": cmd_list,
    "create": cmd_create,
    "register": cmd_register,
    "unregister": cmd_unregister,
    "status": cmd_status,
    "commit": cmd_commit,
    "push": cmd_git_op("push"),
    "pull": cmd_git_op("pull"),
    "log": cmd_log,
    "init": cmd_init,
    "config": cmd_config,
    "doctor": cmd_doctor,
    "check": cmd_check,
}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # --json is a global flag: accept it in any position, like agents write it.
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    args = build_parser().parse_args(argv)
    args.json = as_json
    global _LANG
    _LANG = i18n.get_language(core.CONFIG_FILE)
    try:
        return HANDLERS[args.command](args)
    except ValueError as e:
        return _fail(str(e), args.json)
    except Exception as e:  # agents get a JSON reason, not a traceback
        return _fail(f"{type(e).__name__}: {e}", args.json)


if __name__ == "__main__":
    sys.exit(main())
