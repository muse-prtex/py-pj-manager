#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pjman.py — 総合PJ管理システム（GUI）

プロジェクトの新規作成・既存登録・一覧管理、選んでvenv有効化ターミナルを開く、
git（状態・コミット・プッシュ・プル・ログ）と GitHub（作成・ブラウザで開く）を
1つの画面から操作できます。起動は run.bat のダブルクリックで。
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import pj_core as core

IS_WINDOWS = os.name == "nt"


def open_terminal_with_venv(path: Path) -> None:
    """venv を有効化したターミナルを開く（なければ通常のターミナル）。"""
    if IS_WINDOWS:
        activate = path / ".venv" / "Scripts" / "activate.bat"
        if activate.exists():
            cmdline = f'cmd /k "cd /d ""{path}"" && ""{activate}"""'
        else:
            cmdline = f'cmd /k "cd /d ""{path}"""'
        subprocess.Popen(cmdline, creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        subprocess.Popen(["x-terminal-emulator", "-e", "bash"], cwd=str(path))


def open_in_explorer(path: Path) -> None:
    if IS_WINDOWS:
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])


def open_in_vscode(path: Path) -> tuple[bool, str]:
    import shutil
    if not shutil.which("code"):
        return False, "VS Code の `code` コマンドが見つかりません"
    subprocess.Popen(["code", str(path)])
    return True, "VS Code で開きました"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PJマネージャー — プロジェクト総合管理")
        self.geometry("980x600")
        self.entries: list[dict] = core.load_registry()
        self.config = core.load_config()
        self._build()
        self.refresh_list()

    # ---------- 画面 ----------
    def _build(self) -> None:
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="プロジェクト一覧", font=("", 11, "bold")).pack(anchor="w")
        self.listbox = tk.Listbox(left, width=34, height=24)
        self.listbox.pack(fill="y", expand=True, pady=4)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self.show_detail())
        ttk.Button(left, text="＋ 新規プロジェクト作成", command=self.dialog_new).pack(fill="x", pady=2)
        ttk.Button(left, text="既存フォルダを登録", command=self.dialog_register).pack(fill="x", pady=2)
        ttk.Button(left, text="登録を外す", command=self.do_unregister).pack(fill="x", pady=2)
        ttk.Button(left, text="作成先フォルダの設定", command=self.dialog_config).pack(fill="x", pady=2)

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        self.detail = ttk.Label(right, text="左の一覧からプロジェクトを選んでください",
                                justify="left", font=("", 10))
        self.detail.pack(anchor="w")

        ops = ttk.LabelFrame(right, text="開く")
        ops.pack(fill="x", pady=6)
        ttk.Button(ops, text="ターミナルで開く（venv有効化）", command=self.do_open_terminal).pack(side="left", padx=3, pady=4)
        ttk.Button(ops, text="VS Codeで開く", command=self.do_open_vscode).pack(side="left", padx=3, pady=4)
        ttk.Button(ops, text="フォルダを開く", command=self.do_open_folder).pack(side="left", padx=3, pady=4)

        gitf = ttk.LabelFrame(right, text="Git")
        gitf.pack(fill="x", pady=6)
        ttk.Button(gitf, text="状態を更新", command=self.show_detail).pack(side="left", padx=3, pady=4)
        ttk.Button(gitf, text="コミット", command=self.do_commit).pack(side="left", padx=3, pady=4)
        ttk.Button(gitf, text="プッシュ", command=lambda: self.do_git_op("push")).pack(side="left", padx=3, pady=4)
        ttk.Button(gitf, text="プル", command=lambda: self.do_git_op("pull")).pack(side="left", padx=3, pady=4)
        ttk.Button(gitf, text="ログ（最近10件）", command=self.do_log).pack(side="left", padx=3, pady=4)
        ttk.Button(gitf, text="git init", command=self.do_git_init).pack(side="left", padx=3, pady=4)

        ghf = ttk.LabelFrame(right, text="GitHub")
        ghf.pack(fill="x", pady=6)
        ttk.Button(ghf, text="リポジトリを作成", command=self.do_github_create).pack(side="left", padx=3, pady=4)
        ttk.Button(ghf, text="ブラウザで開く", command=self.do_github_open).pack(side="left", padx=3, pady=4)

        ttk.Label(right, text="実行ログ").pack(anchor="w")
        self.logbox = tk.Text(right, height=14, wrap="word")
        self.logbox.pack(fill="both", expand=True)

    # ---------- 補助 ----------
    def log(self, text: str) -> None:
        self.logbox.insert("end", text + "\n")
        self.logbox.see("end")
        self.update_idletasks()

    def selected(self) -> dict | None:
        sel = self.listbox.curselection()
        if not sel:
            return None
        return self.entries[sel[0]]

    def refresh_list(self) -> None:
        self.entries = core.load_registry()
        self.listbox.delete(0, "end")
        for e in self.entries:
            mark = "" if Path(e["path"]).exists() else "（フォルダなし）"
            self.listbox.insert("end", f'{e["name"]}{mark}')

    def run_async(self, title: str, fn) -> None:
        """時間のかかる処理を別スレッドで実行し、結果をログに出す。"""
        def worker():
            self.after(0, self.log, f"--- {title} ---")
            try:
                out = fn(lambda s: self.after(0, self.log, str(s)))
                if out:
                    self.after(0, self.log, str(out))
            except Exception as ex:  # GUIなので落とさず表示する
                self.after(0, self.log, f"エラー: {ex}")
            self.after(0, self.refresh_list)
            self.after(0, self.show_detail)
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 詳細 ----------
    def show_detail(self) -> None:
        e = self.selected()
        if not e:
            return
        p = Path(e["path"])
        if not p.exists():
            self.detail.config(text=f'{e["name"]}\n場所: {p}\nフォルダが見つかりません（移動・削除された可能性）')
            return
        st = core.git_status(p)
        lines = [
            f'名前: {e["name"]}',
            f'場所: {p}',
            f'登録日: {e.get("created_at", "-")}（{e.get("origin", "-")}）',
            f'venv: {"あり" if core.has_venv(p) else "なし"}',
        ]
        if st["is_git"]:
            lines.append(f'Git: ブランチ {st["branch"] or "-"} / 未コミット {st["dirty"]} 件'
                         f' / 未プッシュ {st["ahead"]} 件 / 未プル {st["behind"]} 件')
            lines.append(f'最終コミット: {st["last_commit"] or "-"}')
            lines.append(f'GitHub: {core.github_web_url(p) or st["remote"] or "未接続"}')
        else:
            lines.append("Git: 管理外（「git init」ボタンで開始できます）")
        self.detail.config(text="\n".join(lines))

    # ---------- 操作 ----------
    def need_selected(self) -> dict | None:
        e = self.selected()
        if not e:
            messagebox.showinfo("未選択", "まず左の一覧からプロジェクトを選んでください")
        return e

    def do_open_terminal(self) -> None:
        e = self.need_selected()
        if e:
            open_terminal_with_venv(Path(e["path"]))
            self.log(f'{e["name"]}: ターミナルを開きました')

    def do_open_folder(self) -> None:
        e = self.need_selected()
        if e:
            open_in_explorer(Path(e["path"]))

    def do_open_vscode(self) -> None:
        e = self.need_selected()
        if e:
            ok, msg = open_in_vscode(Path(e["path"]))
            self.log(msg)

    def do_git_op(self, op: str) -> None:
        e = self.need_selected()
        if not e:
            return
        self.run_async(f"{op}: {e['name']}",
                       lambda log: self._git_result(core.git_op(e["path"], op)))

    @staticmethod
    def _git_result(result: tuple[bool, str]) -> str:
        ok, out = result
        return ("成功\n" if ok else "失敗\n") + (out or "（出力なし）")

    def do_commit(self) -> None:
        e = self.need_selected()
        if not e:
            return
        msg = simpledialog.askstring("コミット", "コミットメッセージ:", parent=self)
        if not msg:
            return
        self.run_async(f"commit: {e['name']}",
                       lambda log: self._git_result(core.commit_all(e["path"], msg)))

    def do_log(self) -> None:
        e = self.need_selected()
        if not e:
            return
        ok, out = core.git_op(e["path"], "log", "--oneline", "-10")
        self.log("--- ログ ---\n" + (out if ok else f"失敗: {out}"))

    def do_git_init(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if core.is_git_repo(Path(e["path"])):
            self.log("すでに git 管理下です")
            return
        self.run_async(f"git init: {e['name']}",
                       lambda log: self._git_result(core.git_op(e["path"], "init", "-b", "main")))

    def do_github_create(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if not messagebox.askyesno("GitHubリポジトリ作成",
                                   f'{e["name"]} のGitHubリポジトリを Private で作成します。よろしいですか？\n'
                                   "（Publicにしたい場合は README のコマンド例をご覧ください）"):
            return
        self.run_async(f"GitHub作成: {e['name']}",
                       lambda log: self._git_result(core.github_create(e["path"], "private", True)))

    def do_github_open(self) -> None:
        e = self.need_selected()
        if not e:
            return
        url = core.github_web_url(Path(e["path"]))
        if url:
            webbrowser.open(url)
        else:
            self.log("GitHub の URL が分かりません（origin 未設定か、GitHub以外のリモートです）")

    def do_unregister(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if messagebox.askyesno("登録を外す",
                               f'{e["name"]} の登録を外しますか？\nフォルダ自体は消えません。'):
            core.unregister(e["name"], self.entries)
            self.entries = core.load_registry()
            self.refresh_list()
            self.log(f'{e["name"]}: 登録を外しました')

    # ---------- ダイアログ ----------
    def dialog_register(self) -> None:
        folder = filedialog.askdirectory(title="登録するプロジェクトのフォルダ")
        if not folder:
            return
        try:
            entry = core.register_existing(folder)
            self.log(f'登録しました: {entry["name"]}')
        except ValueError as ex:
            messagebox.showerror("登録できません", str(ex))
        self.refresh_list()

    def dialog_config(self) -> None:
        folder = filedialog.askdirectory(
            title="新規プロジェクトの作成先フォルダ",
            initialdir=self.config.get("projects_root", ""))
        if folder:
            self.config["projects_root"] = folder
            core.save_config(self.config)
            self.log(f"作成先フォルダを {folder} にしました")

    def dialog_new(self) -> None:
        win = tk.Toplevel(self)
        win.title("新規プロジェクト作成")
        win.geometry("440x330")
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text="プロジェクト名（半角英数字・-・_）").pack(anchor="w", padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var, width=40).pack(anchor="w", padx=10)

        ttk.Label(win, text=f'作成先: {self.config.get("projects_root")}').pack(anchor="w", padx=10, pady=(8, 0))

        ttk.Label(win, text="テンプレート").pack(anchor="w", padx=10, pady=(8, 0))
        tmpl_var = tk.StringVar(value="python")
        ttk.Combobox(win, textvariable=tmpl_var, values=["python", "empty"],
                     state="readonly", width=38).pack(anchor="w", padx=10)

        venv_var = tk.BooleanVar(value=True)
        git_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text="venv（.venv）を作成する", variable=venv_var).pack(anchor="w", padx=10, pady=(8, 0))
        ttk.Checkbutton(win, text="git init して最初のコミットまで作る", variable=git_var).pack(anchor="w", padx=10)

        ttk.Label(win, text="GitHubリポジトリ").pack(anchor="w", padx=10, pady=(8, 0))
        gh_var = tk.StringVar(value="none")
        ttk.Combobox(win, textvariable=gh_var, values=["none", "private", "public"],
                     state="readonly", width=38).pack(anchor="w", padx=10)

        def create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("入力エラー", "プロジェクト名を入力してください", parent=win)
                return
            win.destroy()
            root = self.config.get("projects_root")
            tmpl, mkvenv, gitinit, gh = tmpl_var.get(), venv_var.get(), git_var.get(), gh_var.get()
            self.run_async(
                f"新規作成: {name}",
                lambda log: core.create_project(name, root, template=tmpl,
                                                make_venv=mkvenv, init_git=gitinit,
                                                github=gh, log=log) and "作成完了")

        ttk.Button(win, text="作成する", command=create).pack(pady=14)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
