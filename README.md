# py-pj-manager

A tiny Windows GUI to manage your Python projects in one place: **create, register,
open, and git/GitHub them** from a single window.

No dependencies beyond the Python standard library — clone it, double-click
`run.bat`, and it runs.

![PJ Manager GUI](docs/images/gui.png)

日本語の README は [README.ja.md](README.ja.md) にあります。使い方の
詳細は [docs/usage.md](docs/usage.md)（スクショ付き）を見てください。

## Features

- **Project list** — every registered project at a glance: venv presence, git
  branch, uncommitted / unpushed / unpulled counts, last commit, GitHub URL.
- **Create a project in one go** — type a name and it scaffolds the folder,
  drops in a Python template (`main.py` / `.gitignore` / `requirements.txt` /
  `README.md`), creates `.venv`, runs `git init` with an initial commit, and can
  optionally create the GitHub repository (private or public) — then registers
  the project in the list.
- **Register existing folders** — projects you already have can join the list too.
- **Open things fast** — open a project in a venv-activated terminal, in VS Code,
  or in Explorer.
- **Git built in** — refresh status, commit (with a message field), push, pull,
  view the log, `git init`.
- **Keyboard shortcuts** — `Ctrl+N` new project, `Ctrl+O` register a folder,
  `F5` / `Ctrl+R` refresh, `Enter` open the selected project in a terminal,
  `Delete` unregister, `Ctrl+Q` quit (listed at the bottom-left of the GUI).
- **GitHub via `gh`** — create a repository or open it in the browser, using the
  official GitHub CLI.

## Quick start

Requirements: Windows, Python 3.10+ (with the `py` launcher). The GitHub
features additionally need the [`gh` CLI](https://cli.github.com/) with
`gh auth login` done once — everything else works without it.

```powershell
git clone https://github.com/muse-prtex/py-pj-manager.git
cd py-pj-manager
```

Then double-click **`run.bat`** (or run `py pjman.py`).

New projects are created under `~/Projects` by default; change it from
“作成先フォルダの設定” (creation folder setting) at the bottom-left of the
window. The setting is stored in `config.json`.

Display language is Japanese by default. Switch it from the **言語 / Language**
dropdown at the bottom-left of the window, or with
`pj-manager config set-language en` (`ja` to switch back). The CLI's
human-readable output and the tkinter GUI follow the setting; `--json`
output does not change with the language. The Tauri desktop UI is still
Japanese-only for now and follows in a later session.

## Notes

- If the initial commit is skipped, git identity is the usual cause. Set it once:
  `git config --global user.name "Your Name"` and
  `git config --global user.email "you@example.com"`.
- Unregistering a project never deletes its folder. By design, this tool never
  deletes project folders.

## Files

## Repository layout

The code lives in a standard `src/` package layout, so the project can grow
without a big reshuffle later:

```
src/pj_manager/
    __init__.py    package version
    app.py         the GUI (tkinter)
    core.py        project registry, creation, git/GitHub logic (GUI-free)
    cli.py         command-line face for scripts and AI agents (AGENTS.md)
    i18n.py        UI string dictionaries (ja/en) and language resolution
    __main__.py    enables `python -m pj_manager`
tests/             unittest suite for core.py (standard library only)
pyproject.toml     packaging (`pip install -e .` installs the `pj-manager` command)
pjman.py           compatibility launcher (`py pjman.py` still works)
run.bat            launcher (sets PYTHONPATH and runs the package)
```

`projects.json` (project registry) and `config.json` (settings) are
auto-generated in the repository root and git-ignored.

## Desktop app (modern UI)

A Tauri-based desktop app lives in [`desktop/`](desktop/README.md) — dark
sidebar, cards, badges, search. It drives the same Python core through the
CLI below, so both faces always agree. The tkinter GUI remains available as
a zero-dependency fallback (`run.bat`).

![Desktop app](docs/images/desktop.png)

## CLI for scripts and AI agents

Everything the GUI does is also available headlessly. Install it once
from a clone and the `pj-manager` command is on your PATH (still no
dependencies beyond the standard library):

```powershell
pip install -e .        # or `pip install .` for a plain install
pj-manager list --json
pj-manager create my-app --json
pj-manager status my-app --json
pj-manager commit my-app -m "wip" --json
pj-manager doctor --json
pj-manager check --json
```

Without installing, the same CLI runs with `PYTHONPATH=src`:

```powershell
py -m pj_manager.cli list --json
py -m pj_manager.cli create my-app --json

With `--json`, stdout is a single JSON object and the exit code is 0/1 —
no prompts, ever. Agents: read [AGENTS.md](AGENTS.md) for the full contract,
including the `PJ_MANAGER_DATA_DIR` sandbox variable.

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
Good first areas: English UI localization (the GUI is currently Japanese),
macOS/Linux support, and more tests for `core.py`.

## License

MIT License — see [LICENSE](LICENSE).
