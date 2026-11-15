# Contributing to py-pj-manager

Thanks for your interest! Issues, feature ideas, and pull requests are all
welcome. （日本語でも大丈夫です。）

## Ground rules

- **Standard library only.** The project's core promise is "clone and it runs",
  so contributions must not add third-party dependencies.
- **Windows first.** The GUI targets Windows (tkinter). Platform-specific code
  should be guarded so `pj_core.py` stays importable elsewhere.
- **Never delete user folders.** Unregistering a project must not remove files;
  please keep that safety property in any change.

## Development setup

You need Python 3.10+ on Windows. There is nothing to install:

```powershell
git clone https://github.com/muse-prtex/py-pj-manager.git
cd py-pj-manager
py pjman.py        # launch the GUI (or: run.bat)
```

The code is a package under `src/pj_manager/` (`app.py` = GUI, `core.py` =
logic). Run the test suite — standard library `unittest` only:

```powershell
py -m unittest discover -s tests -v
```

`projects.json` and `config.json` are generated next to the scripts and are
git-ignored — safe to delete while testing.

## Making a change

1. Fork the repository and create a topic branch.
2. Keep changes focused; match the existing style (plain functions in
   `core.py`, tkinter widgets in `app.py`). Add tests under `tests/` when you
   change `core.py`.
3. If you touch project creation or git operations, test the flow end to end
   with a throwaway folder and a local git repository.
4. Open a pull request describing what changed and how you verified it.

## Ideas that would especially help

- English (or other language) localization of the GUI — currently Japanese.
- More automated tests for `core.py`.
- macOS / Linux support for the "open terminal / editor" actions.

## Reporting bugs

Open an issue with your Windows and Python versions, what you did, what you
expected, and what happened. Please don't include personal paths or tokens
beyond what's needed to reproduce the problem.
