# 使い方 (usage)

py-pj-manager（PJマネージャー）は、Python プロジェクトの「選ぶ・作る・
開く・Git/GitHub で管理する」を1つの画面にまとめた道具です。追加の依存は
なく、Python 標準機能だけで動きます。

> 実行例のパスは実行したマシンのものです。Windows では
> `C:\Users\...` のようなパスになりますが、コマンドと出力の形は同じです。

## 目次

- [インストールと起動](#インストールと起動)
- [GUI の使い方](#gui-の使い方)
- [デスクトップアプリ（モダン UI）](#デスクトップアプリモダン-ui)
- [表示言語の切替](#表示言語の切替)
- [CLI（コマンドライン）](#cliコマンドライン)
- [データファイルとサンドボックス](#データファイルとサンドボックス)
- [トラブルシューティング](#トラブルシューティング)

## インストールと起動

要件：Python 3.10+。GitHub 機能だけ、別途 [`gh` CLI](https://cli.github.com/)
（`gh auth login` を一度だけ実行）が必要です。それ以外は `gh` なしで動きます。

```powershell
git clone https://github.com/muse-prtex/py-pj-manager.git
cd py-pj-manager
```

起動は2通りあります。

- **GUI（tkinter、依存ゼロ）**：`run.bat` をダブルクリック（または `py pjman.py`）。
- **CLI を `pj-manager` コマンドで使う**：一度だけ `pip install -e .`
  を実行すると `pj-manager` コマンドが使えるようになります
  （`pip install .` でも同じです。依存はゼロのままです）。

## GUI の使い方

![PJマネージャーのメイン画面](images/gui.png)

左がプロジェクト一覧、右が選んだプロジェクトの詳細です。

キーボードショートカット：`Ctrl+N` 新規作成、`Ctrl+O` 既存フォルダを登録、`F5` / `Ctrl+R` 更新、`Enter` 選択中のプロジェクトをターミナルで開く、`Delete` 登録解除、`Ctrl+Q` 終了。画面左下にも一覧が出ています。

### プロジェクトを選ぶ

一覧から選ぶと、右側に venv の有無、Git のブランチ・未コミット件数・
未プッシュ/未プル件数、最終コミット、GitHub の URL が表示されます。

### 新規プロジェクトを作る

左下の「＋ 新規プロジェクト作成」を押して名前を入れるだけです。
フォルダ作成 → テンプレート配置（`main.py` / `.gitignore` /
`requirements.txt` / `README.md`）→ `.venv` 作成 → `git init` と
最初のコミット → 一覧への登録まで一括で行います。任意で GitHub
リポジトリの作成（Private/Public）もできます。

作成先はホームフォルダの `Projects` が既定です。画面左下の
「作成先フォルダの設定」から変えられます（`config.json` に保存）。

### 既存フォルダを登録する

「既存フォルダを登録」から、すでにあるプロジェクトのフォルダを選びます。
venv や git が無いフォルダも登録できます（その場合は「開く」や
`git init` で後から整えられます）。登録を外してもフォルダ自体は
消えません。この道具からプロジェクトフォルダを削除することはありません。

### 開く

選んだプロジェクトを「venv 有効化済みのターミナル」「VS Code」
「フォルダ」で開けます。

### Git / GitHub

詳細の「Git」カードから状態更新・コミット（メッセージ入力つき）・
プッシュ・プル・ログ表示・`git init` ができます。「GitHub」カードから
リポジトリ作成とブラウザで開く操作ができます（`gh` CLI が必要）。

## デスクトップアプリ（モダン UI）

Tauri 製のデスクトップ版が [`desktop/`](../desktop/README.md) にあります。
ダークサイドバー、カード表示、バッジ、検索つきで、日常使いの本命です。
中身の処理は CLI 経由で Python コアを呼ぶだけなので、どの画面からでも
状態は一致します。tkinter 版 GUI は依存ゼロの予備として `run.bat` から
使えます。

![デスクトップアプリ](images/desktop.png)

プロジェクトが0件のときは、代わりに新規作成と登録への入口が出ます。

![プロジェクト0件の空状態](images/desktop-empty.png)

新規作成はモーダルで名前を入れるだけです。名前が不正なときは
欄の下に理由が出て、モーダルは開いたままになります。
モーダルは Esc キーでも背景クリックでも閉じられます。

![新規作成モーダル](images/desktop-modal-new.png)

## 表示言語の切替

表示言語は日本語が既定です。GUI 左下の「言語」から切り替えるか、CLI で
`pj-manager config set-language en` を実行してください（`ja` で日本語に
戻ります）。CLI の人間向け出力と tkinter GUI が切り替わります。
`--json` の出力は言語で変わりません。Tauri 製デスクトップ UI も
サイドバー左下の「言語」から同じ設定で切り替わります。

![英語表示の GUI](images/gui-en.png)

## CLI（コマンドライン）

GUI の操作はすべてコマンドラインからも実行できます。`--json` を付けると
標準出力が JSON 1オブジェクトになり、終了コードは 0（成功）/1（失敗）。
対話プロンプトはありません。スクリプトや AI エージェント向けの契約は
[AGENTS.md](../AGENTS.md) にあります。

```console
$ pj-manager list
demo-app                 /home/hatch/Projects/demo-app  [venv git:main]
plain-tool               /tmp/pj-day/plain-tool  [no-venv]

$ pj-manager status demo-app
demo-app: /home/hatch/Projects/demo-app
  venv: yes
  git: branch=main dirty=0 ahead=0 behind=0
  last: 40fe96f 2026-11-16 Initial commit
```

よく使うコマンド：

| コマンド | 内容 |
| --- | --- |
| `pj-manager list` | 登録中のプロジェクト一覧 |
| `pj-manager create my-app` | 新規作成（venv + git init + 初回コミット付き） |
| `pj-manager register <フォルダ>` | 既存フォルダを登録 |
| `pj-manager unregister <名前>` | 登録を外す（フォルダは残る） |
| `pj-manager status <名前>` | 1件の状態（venv / git / 最終コミット） |
| `pj-manager commit <名前> -m "wip"` | コミット |
| `pj-manager push` / `pull` / `log` / `init` | Git 操作 |
| `pj-manager doctor` | 環境の点検 |
| `pj-manager check` | 全プロジェクトの健全性を一括表示 |
| `pj-manager config set-language en` | 表示言語を英語に（`ja` で日本語へ） |

### doctor — 環境の点検

Python / venv / git / gh / 作成先フォルダ / データフォルダ / 登録簿 /
設定の8項目を点検します。`--json` では `{"ok", "status", "checks",
"summary"}` を返します。終了コードは fail があるときだけ 1 で、
warn だけなら 0 です（gh 未ログインや、登録したフォルダが無くなった
場合は warn です）。

```console
$ pj-manager doctor
✓ python: Python 3.12.3
✓ venv: venv モジュールが使えます
✓ git: git version 2.43.0
! gh: gh CLI はありますがログインしていません — ターミナルで `gh auth login` を実行してください
✓ projects_root: 存在します: /home/hatch/Projects
✓ data_dir: 書き込めます: /tmp/pj-day/data
✓ registry: 2 件登録中（フォルダは全て存在します）
✓ config: まだありません（既定値で動きます）
status: warn (7 ok / 1 warn / 0 fail)
```

![doctor の実行例](images/cli-doctor.png)

### check — 全プロジェクトの健全性を一括表示

登録中の全プロジェクトを1つの JSON
`{"ok", "projects", "summary"}` で出力します。各プロジェクトは
`state`（ok / attention / missing）、`has_venv`、git の数値
（branch / dirty / ahead / behind / last_commit）と短い `issues`
タグ一覧（`dirty:2` / `ahead:1` / `behind:1` / `no-venv` /
`not-git` / `missing`）を持ちます。全体の `ok` はフォルダが無い登録
（missing）があるときだけ False（終了コード 1）です。dirty / ahead /
behind / venv 無しは attention であって失敗ではありません
（doctor と同じ考え方です）。

```console
$ pj-manager check
demo-app                 [ok] venv main dirty=0 ahead=0 behind=0
plain-tool               [attention] no-venv not-git (not-git, no-venv)
check: 2 projects (1 ok / 1 attention / 0 missing)
```

![check の実行例](images/cli-check.png)

## データファイルとサンドボックス

- `projects.json` … プロジェクト一覧（リポジトリのルートに自動生成）
- `config.json` … 設定（作成先フォルダ・表示言語など、同上）
- どちらも git 管理外です。

登録簿や設定を壊さずに試したいときは、環境変数
`PJ_MANAGER_DATA_DIR` でデータフォルダを差し替えられます
（このドキュメントの実行例もサンドボックスで確認しています）。

```console
$ PJ_MANAGER_DATA_DIR=/tmp/pj-day/data pj-manager list
```

## トラブルシューティング

- **最初のコミットがスキップされる**：git のユーザー名/メールが
  未設定のことが多いです。一度だけ設定してください。
  `git config --global user.name "あなたの名前"` と
  `git config --global user.email "あなたのメール"`。
- **GitHub 機能が使えない**：`gh` CLI の未導入か未ログインです。
  https://cli.github.com/ から入れて、ターミナルで一度だけ
  `gh auth login` してください。未導入・未ログインでも、GitHub 以外の
  機能はそのまま使えます。`doctor` でも確認できます。
- **登録したフォルダが無くなった**：`list` には出ますが、`check` で
  missing、`doctor` で warn になります。フォルダを戻すか、
  `unregister` で登録を外してください（フォルダの削除はしません）。
- **登録簿（projects.json）が壊れた**：保存前に
  `projects.json.bak-<日時>` へ退避する仕組みがあります。壊れた
  登録簿は `doctor` が fail として報告します。バックアップから戻すか、
  登録し直してください。
