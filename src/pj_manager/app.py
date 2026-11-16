#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pj_manager/app.py — 総合PJ管理システム（GUI）

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

from pj_manager import core, i18n

IS_WINDOWS = os.name == "nt"

# ---------- テーマ（モダンなフラットデザイン） ----------
ACCENT = "#2f6fed"
ACCENT_DARK = "#1f55c4"
APP_BG = "#eef0f3"
CARD_BG = "#ffffff"
TEXT = "#1c2330"
MUTED = "#66707f"
SIDE_BG = "#171c26"
SIDE_PANEL = "#1f2634"
SIDE_FG = "#e6e9f0"
SIDE_SUB = "#8b93a5"
LOG_BG = "#10141c"
LOG_FG = "#c9d4e3"

UI_FONT = "Yu Gothic UI" if IS_WINDOWS else ""
MONO_FONT = "Consolas" if IS_WINDOWS else "DejaVu Sans Mono"


def font(size: int, weight: str = "") -> tuple:
    return (UI_FONT, size, weight) if weight else (UI_FONT, size)


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
        return False, i18n.t("app_vscode_not_found")
    subprocess.Popen(["code", str(path)])
    return True, i18n.t("app_vscode_opened")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.config = core.load_config()
        self.lang = i18n.normalize_language(self.config.get("language"))
        self.title(self.tr("app_title"))
        self.geometry("1080x660")
        self.minsize(1020, 620)
        self.configure(bg=APP_BG)
        self.entries: list[dict] = core.load_registry()
        self._setup_styles()
        self._build()
        self.refresh_list()

    def tr(self, key: str, **kwargs) -> str:
        """この画面の表示文字列（辞書 i18n.STRINGS から取る）。"""
        return i18n.t(key, lang=self.lang, **kwargs)

    def set_language(self, lang: str) -> None:
        """言語を切り替え、config に保存して画面を作り直す。"""
        lang = i18n.normalize_language(lang)
        if lang == self.lang:
            return
        self.lang = lang
        self.config["language"] = lang
        core.save_config(self.config)
        self._rebuild()

    def _rebuild(self) -> None:
        """全ウィジェットを捨てて _build から作り直す（言語切替用）。

        切替前に選んでいたプロジェクトがあれば、作り直し後に
        選び直して詳細も出し直す（言語を変えただけで表示が
        プレースホルダに戻らないようにするため）。
        """
        selected = self.selected()
        selected_name = selected["name"] if selected else None
        for w in self.winfo_children():
            w.destroy()
        self.title(self.tr("app_title"))
        self._build()
        self.refresh_list()
        if selected_name:
            for i, e in enumerate(self.entries):
                if e["name"] == selected_name:
                    self.listbox.selection_set(i)
                    self.show_detail()
                    break

    def _setup_styles(self) -> None:
        st = ttk.Style(self)
        st.theme_use("clam")  # 色を自由に変えられる土台テーマ
        st.configure("TFrame", background=APP_BG)
        st.configure("Card.TFrame", background=CARD_BG)
        st.configure("Side.TFrame", background=SIDE_BG)
        st.configure("TLabel", background=APP_BG, foreground=TEXT, font=font(10))
        st.configure("Card.TLabel", background=CARD_BG, foreground=TEXT, font=font(10))
        st.configure("Section.TLabel", background=CARD_BG, foreground=MUTED,
                     font=font(9, "bold"))
        st.configure("SideTitle.TLabel", background=SIDE_BG, foreground="#ffffff",
                     font=font(15, "bold"))
        st.configure("SideSub.TLabel", background=SIDE_BG, foreground=SIDE_SUB,
                     font=font(8))
        st.configure("SideSection.TLabel", background=SIDE_BG, foreground=SIDE_SUB,
                     font=font(9, "bold"))
        st.configure("TButton", background="#e3e7ee", foreground=TEXT,
                     borderwidth=0, focusthickness=0, padding=(11, 6), font=font(10))
        st.map("TButton",
               background=[("active", "#d3dae6"), ("pressed", "#c3ccdc"),
                           ("disabled", "#eceff4")],
               foreground=[("disabled", "#9aa3b2")])
        st.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                     borderwidth=0, focusthickness=0, padding=(11, 7),
                     font=font(10, "bold"))
        st.map("Accent.TButton",
               background=[("active", ACCENT_DARK), ("pressed", ACCENT_DARK),
                           ("disabled", "#a9c2f5")],
               foreground=[("disabled", "#ffffff")])
        st.configure("Side.TButton", background="#232a38", foreground=SIDE_FG,
                     borderwidth=0, focusthickness=0, padding=(11, 6), font=font(10))
        st.map("Side.TButton",
               background=[("active", "#2d3648"), ("pressed", "#2d3648")])
        st.configure("TCheckbutton", background=APP_BG, foreground=TEXT, font=font(10))
        st.configure("TCombobox", padding=(4, 3))
        st.configure("TEntry", padding=(4, 3))

    # ---------- 画面 ----------
    def _build(self) -> None:
        # 左サイドバー（ダーク）
        side = tk.Frame(self, bg=SIDE_BG, width=296)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        head = tk.Frame(side, bg=SIDE_BG)
        head.pack(fill="x", padx=16, pady=(16, 4))
        ttk.Label(head, text=self.tr("app_sidebar_title"), style="SideTitle.TLabel").pack(anchor="w")
        ttk.Label(head, text="PROJECT MANAGER", style="SideSub.TLabel").pack(anchor="w", pady=(1, 0))
        ttk.Label(side, text=self.tr("app_section_projects"), style="SideSection.TLabel").pack(
            anchor="w", padx=16, pady=(14, 4))
        self.listbox = tk.Listbox(
            side, width=34, height=10,
            bg=SIDE_PANEL, fg=SIDE_FG,
            selectbackground=ACCENT, selectforeground="#ffffff",
            relief="flat", borderwidth=0, highlightthickness=0,
            activestyle="none", font=font(10), exportselection=False)
        self.listbox.pack(fill="both", expand=True, padx=12)
        self.listbox.bind("<<ListboxSelect>>", lambda _e: self.show_detail())
        btns = tk.Frame(side, bg=SIDE_BG)
        btns.pack(fill="x", padx=12, pady=12)
        ttk.Button(btns, text=self.tr("app_btn_new"), style="Accent.TButton",
                   command=self.dialog_new).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text=self.tr("app_btn_register"), style="Side.TButton",
                   command=self.dialog_register).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text=self.tr("app_btn_unregister"), style="Side.TButton",
                   command=self.do_unregister).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text=self.tr("app_btn_config"), style="Side.TButton",
                   command=self.dialog_config).pack(fill="x")
        lang_row = tk.Frame(side, bg=SIDE_BG)
        lang_row.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Label(lang_row, text=self.tr("app_language_label"),
                  style="SideSub.TLabel").pack(side="left")
        self.lang_combo = ttk.Combobox(
            lang_row, values=["日本語", "English"], state="readonly", width=10)
        self.lang_combo.set("日本語" if self.lang == "ja" else "English")
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>",
                             lambda _e: self.set_language(
                                 "ja" if self.lang_combo.get() == "日本語" else "en"))
        from pj_manager import __version__
        ttk.Label(side, text=f"v{__version__}", style="SideSub.TLabel").pack(
            anchor="w", padx=16, pady=(0, 10))

        # 右メインエリア
        right = ttk.Frame(self, padding=(14, 12, 14, 12))
        right.pack(side="left", fill="both", expand=True)

        card = ttk.Frame(right, style="Card.TFrame", padding=14)
        card.pack(fill="x")
        self.detail = tk.Label(card, text=self.tr("app_detail_placeholder"),
                               justify="left", anchor="nw", bg=CARD_BG, fg=TEXT,
                               font=font(10))
        self.detail.pack(fill="x")

        def section(title: str, buttons: list) -> None:
            frame = ttk.Frame(right, style="Card.TFrame", padding=(14, 10, 14, 12))
            frame.pack(fill="x", pady=(10, 0))
            ttk.Label(frame, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 6))
            row = ttk.Frame(frame, style="Card.TFrame")
            row.pack(fill="x")
            for text_, cmd, style in buttons:
                ttk.Button(row, text=text_, style=style, command=cmd).pack(
                    side="left", padx=(0, 6))

        section(self.tr("app_section_open"), [
            (self.tr("app_btn_terminal"), self.do_open_terminal, "Accent.TButton"),
            (self.tr("app_btn_vscode"), self.do_open_vscode, "TButton"),
            (self.tr("app_btn_folder"), self.do_open_folder, "TButton"),
        ])
        section("Git", [
            (self.tr("app_btn_refresh"), self.show_detail, "TButton"),
            (self.tr("app_btn_commit"), self.do_commit, "TButton"),
            (self.tr("app_btn_push"), lambda: self.do_git_op("push"), "TButton"),
            (self.tr("app_btn_pull"), lambda: self.do_git_op("pull"), "TButton"),
            (self.tr("app_btn_log"), self.do_log, "TButton"),
            (self.tr("app_btn_git_init"), self.do_git_init, "TButton"),
        ])
        section("GitHub", [
            (self.tr("app_btn_gh_create"), self.do_github_create, "TButton"),
            (self.tr("app_btn_gh_open"), self.do_github_open, "TButton"),
        ])

        ttk.Label(right, text=self.tr("app_log_label")).pack(anchor="w", pady=(12, 4))
        self.logbox = tk.Text(right, height=14, wrap="word",
                              bg=LOG_BG, fg=LOG_FG, relief="flat", borderwidth=0,
                              highlightthickness=0, font=(MONO_FONT, 9),
                              padx=10, pady=8)
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
            mark = "" if Path(e["path"]).exists() else self.tr("app_folder_missing_mark")
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
                self.after(0, self.log, self.tr("app_log_error", error=ex))
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
            self.detail.config(text="\n".join([
                self.tr("app_detail_name", name=e["name"]),
                self.tr("app_detail_location", path=p),
                self.tr("app_detail_folder_missing")]))
            return
        st = core.git_status(p)
        lines = [
            self.tr("app_detail_name", name=e["name"]),
            self.tr("app_detail_location", path=p),
            self.tr("app_detail_registered", date=e.get("created_at", "-"),
                    origin=e.get("origin", "-")),
            self.tr("app_detail_venv",
                    value="yes" if core.has_venv(p) else "no"),
        ]
        if st["is_git"]:
            lines.append(self.tr("app_detail_git", branch=st["branch"] or "-",
                                 dirty=st["dirty"], ahead=st["ahead"],
                                 behind=st["behind"]))
            lines.append(self.tr("app_detail_last_commit",
                                 last=st["last_commit"] or "-"))
            lines.append(self.tr("app_detail_github",
                                 url=core.github_web_url(p) or st["remote"]
                                 or self.tr("app_detail_not_connected")))
        else:
            lines.append(self.tr("app_detail_not_git"))
        self.detail.config(text="\n".join(lines))

    # ---------- 操作 ----------
    def need_selected(self) -> dict | None:
        e = self.selected()
        if not e:
            messagebox.showinfo(self.tr("app_msg_not_selected_title"),
                                self.tr("app_msg_not_selected"))
        return e

    def do_open_terminal(self) -> None:
        e = self.need_selected()
        if e:
            open_terminal_with_venv(Path(e["path"]))
            self.log(self.tr("app_log_terminal_opened", name=e["name"]))

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

    def _git_result(self, result: tuple[bool, str]) -> str:
        ok, out = result
        status = self.tr("app_git_success") if ok else self.tr("app_git_failed")
        return status + "\n" + (out or self.tr("app_git_no_output"))

    def do_commit(self) -> None:
        e = self.need_selected()
        if not e:
            return
        msg = simpledialog.askstring(self.tr("app_commit_title"),
                                     self.tr("app_commit_prompt"), parent=self)
        if not msg:
            return
        self.run_async(f"commit: {e['name']}",
                       lambda log: self._git_result(core.commit_all(e["path"], msg)))

    def do_log(self) -> None:
        e = self.need_selected()
        if not e:
            return
        ok, out = core.git_op(e["path"], "log", "--oneline", "-10")
        self.log(self.tr("app_log_header") + "\n"
                 + (out if ok else self.tr("app_log_failed", out=out)))

    def do_git_init(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if core.is_git_repo(Path(e["path"])):
            self.log(self.tr("app_log_already_git"))
            return
        self.run_async(f"git init: {e['name']}",
                       lambda log: self._git_result(core.git_op(e["path"], "init", "-b", "main")))

    def do_github_create(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if not messagebox.askyesno(self.tr("app_gh_create_title"),
                                   self.tr("app_gh_create_body", name=e["name"])):
            return
        self.run_async(self.tr("app_gh_create_log", name=e["name"]),
                       lambda log: self._git_result(core.github_create(e["path"], "private", True)))

    def do_github_open(self) -> None:
        e = self.need_selected()
        if not e:
            return
        url = core.github_web_url(Path(e["path"]))
        if url:
            webbrowser.open(url)
        else:
            self.log(self.tr("app_gh_url_unknown"))

    def do_unregister(self) -> None:
        e = self.need_selected()
        if not e:
            return
        if messagebox.askyesno(self.tr("app_unregister_title"),
                               self.tr("app_unregister_body", name=e["name"])):
            core.unregister(e["name"], self.entries)
            self.entries = core.load_registry()
            self.refresh_list()
            self.log(self.tr("app_log_unregistered", name=e["name"]))

    # ---------- ダイアログ ----------
    def dialog_register(self) -> None:
        folder = filedialog.askdirectory(title=self.tr("app_register_dialog_title"))
        if not folder:
            return
        try:
            entry = core.register_existing(folder)
            self.log(self.tr("app_log_registered", name=entry["name"]))
        except ValueError as ex:
            messagebox.showerror(self.tr("app_register_error_title"), str(ex))
        self.refresh_list()

    def dialog_config(self) -> None:
        folder = filedialog.askdirectory(
            title=self.tr("app_config_dialog_title"),
            initialdir=self.config.get("projects_root", ""))
        if folder:
            self.config["projects_root"] = folder
            core.save_config(self.config)
            self.log(self.tr("app_log_root_set", folder=folder))

    def dialog_new(self) -> None:
        win = tk.Toplevel(self)
        win.title(self.tr("app_new_dialog_title"))
        win.geometry("460x380")
        win.configure(bg=APP_BG)
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text=self.tr("app_new_name_label")).pack(anchor="w", padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        ttk.Entry(win, textvariable=name_var, width=40).pack(anchor="w", padx=10)

        ttk.Label(win, text=self.tr("app_new_root_label",
                                     root=self.config.get("projects_root"))).pack(anchor="w", padx=10, pady=(8, 0))

        ttk.Label(win, text=self.tr("app_new_template_label")).pack(anchor="w", padx=10, pady=(8, 0))
        tmpl_var = tk.StringVar(value="python")
        ttk.Combobox(win, textvariable=tmpl_var, values=["python", "empty"],
                     state="readonly", width=38).pack(anchor="w", padx=10)

        venv_var = tk.BooleanVar(value=True)
        git_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text=self.tr("app_new_venv_label"), variable=venv_var).pack(anchor="w", padx=10, pady=(8, 0))
        ttk.Checkbutton(win, text=self.tr("app_new_git_label"), variable=git_var).pack(anchor="w", padx=10)

        ttk.Label(win, text=self.tr("app_new_github_label")).pack(anchor="w", padx=10, pady=(8, 0))
        gh_var = tk.StringVar(value="none")
        ttk.Combobox(win, textvariable=gh_var, values=["none", "private", "public"],
                     state="readonly", width=38).pack(anchor="w", padx=10)

        def create():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror(self.tr("app_input_error_title"),
                                     self.tr("app_new_name_required"), parent=win)
                return
            win.destroy()
            root = self.config.get("projects_root")
            tmpl, mkvenv, gitinit, gh = tmpl_var.get(), venv_var.get(), git_var.get(), gh_var.get()
            self.run_async(
                self.tr("app_new_title", name=name),
                lambda log: core.create_project(name, root, template=tmpl,
                                                make_venv=mkvenv, init_git=gitinit,
                                                github=gh, log=log) and self.tr("app_new_done"))

        ttk.Button(win, text=self.tr("app_btn_create"), style="Accent.TButton",
                   command=create).pack(pady=16)


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
