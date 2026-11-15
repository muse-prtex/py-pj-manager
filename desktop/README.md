# PJ Manager Desktop (Tauri)

The modern desktop UI for py-pj-manager, built with [Tauri](https://tauri.app/)
(Rust shell + web frontend). It is the recommended face for daily use.

## How it works

The shell holds **no project logic**. Every operation goes through the
Python core's CLI:

```
pj-manager-desktop ──(spawn)──> python -m pj_manager.cli ... --json
```

So the desktop app, the tkinter GUI, scripts and AI agents all share one
core and one state (`projects.json`). See `../AGENTS.md` for the CLI
contract.

The shell finds the Python package by looking for a `src/` folder that
contains `pj_manager/cli.py`, in this order:

1. the `PJ_MANAGER_SRC` environment variable,
2. next to / above the executable (`src/`, `../src/`, `../../src/`, …),
3. the current directory's `src/`.

If you run the packaged executable outside this repository, set
`PJ_MANAGER_SRC` to the repository's `src` folder. Python 3.10+ must be on
the PATH (`py` on Windows, `python3` elsewhere).

## Develop / build

Icons are binary and therefore not committed; generate them once:

```
python3 desktop/tools/make_icons.py   # requires Pillow
```

```
cd desktop/src-tauri
cargo build            # debug build for your platform
cargo xwin build --release --target x86_64-pc-windows-msvc   # Windows exe (cross)
```

The frontend is a single dependency-free `desktop/ui/index.html`. Opened in
a plain browser it runs in a demo mode with sample data, which is handy for
design work.

## Layout

```
desktop/
  ui/index.html          the whole frontend (HTML/CSS/JS, no build step)
  src-tauri/
    src/main.rs          two commands: pj (CLI bridge), open_target (OS open)
    tauri.conf.json
    capabilities/        Tauri permissions (core + folder dialog)
```
