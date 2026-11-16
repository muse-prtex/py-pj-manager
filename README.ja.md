# py-pj-manager（PJマネージャー）

プロジェクトの「選ぶ・作る・開く・Git/GitHubで管理する」を1つの画面にまとめた道具です。
追加の依存はなく、Python標準機能だけで動きます。

![PJマネージャーのメイン画面](docs/images/gui.png)

English README: [README.md](README.md)
使い方の詳細は [docs/usage.md](docs/usage.md)（スクショ付き）を見てください。

## 起動

`run.bat` をダブルクリック（追加のインストールは不要で、Python標準機能だけで動きます）。

## できること

- **プロジェクト一覧**：登録したプロジェクトを一覧表示。選ぶと venv の有無、Gitのブランチ・未コミット件数・未プッシュ/未プル件数、最終コミット、GitHubのURLが分かります
- **新規プロジェクト作成**：名前を入れるだけで、フォルダ作成 → テンプレート配置（Python用：`main.py` / `.gitignore` / `requirements.txt` / `README.md`）→ `.venv` 作成 → `git init` と最初のコミット → 任意で GitHub リポジトリ作成（Private/Public）まで一括で行い、一覧に登録します
- **既存フォルダを登録**：すでにあるプロジェクトも一覧に加えられます
- **開く系**：選んだプロジェクトを「venv有効化済みのターミナル」「VS Code」「フォルダ」で開けます
- **Git**：状態更新、コミット（メッセージ入力つき）、プッシュ、プル、ログ表示、git init
- **GitHub**：リポジトリ作成ボタン（Private）、ブラウザで開く。Publicで作りたい／細かい指定をしたい場合は、ターミナルから `gh` を直接使うこともできます

## 新規プロジェクトの作成先

初期設定はホームフォルダの `Projects` です。画面左下の「作成先フォルダの設定」から変更できます（設定は `config.json` に保存されます）。

表示言語は日本語が既定です。画面左下の「言語」から切り替えるか、CLI で
`pj-manager config set-language en` を実行してください（`ja` で日本語に
戻ります）。CLI の人間向け出力と tkinter GUI が切り替わります。`--json`
の出力は言語で変わりません。Tauri 製デスクトップ UI は今のところ日本語
のままで、後のセッションで追随します。

## GitHub 連携の前提

GitHub機能は GitHub公式の `gh` CLI を使います。未導入の場合は https://cli.github.com/ から入れて、ターミナルで一度だけ `gh auth login` してください。未導入・未ログインでも、GitHub以外の機能はそのまま使えます。

最初のコミットがスキップされる場合は、git のユーザー名/メールが未設定のことが多いです。その場合は一度だけ：

```
git config --global user.name "あなたの名前"
git config --global user.email "あなたのメール"
```

## ファイル構成

コードは `src/` パッケージ構成です（今後大きくなっても再編しなくて済む形）。

- `src/pj_manager/app.py` … 画面（GUI）本体
- `src/pj_manager/core.py` … 一覧管理・作成・git/GitHub操作のロジック
- `src/pj_manager/cli.py` … スクリプト／AIエージェント用 CLI（AGENTS.md 参照）
- `src/pj_manager/i18n.py` … 表示文字列の辞書（日本語／英語）と表示言語の解決
- `src/pj_manager/__main__.py` … `python -m pj_manager` 用
- `tests/` … core の unittest
- `pjman.py` … 互換用ランチャー（従来どおり `py pjman.py` でも起動できます）
- `run.bat` … 起動用
- `projects.json` … プロジェクト一覧（リポジトリのルートに自動生成）
- `config.json` … 設定（同上）

登録を外してもフォルダ自体は消えません（安全のため、この道具からはフォルダの削除はしません）。

## デスクトップアプリ（モダンUI）

Tauri 製のデスクトップ版が [`desktop/`](desktop/README.md) にあります
（ダークサイドバー、カード表示、バッジ、検索つき）。中身の処理は下記
CLI 経由で Python コアを呼ぶだけなので、どの画面からでも状態は一致
します。tkinter 版 GUI は依存ゼロの予備として `run.bat` から使えます。

![デスクトップアプリ](docs/images/desktop.png)

## スクリプト／AIエージェント用 CLI

GUI の操作はすべてコマンドラインからも実行できます。クローンした
フォルダで一度 `pip install -e .` すれば `pj-manager` コマンドが
使えるようになります（追加の依存はなく、Python標準機能だけです）：

```
pip install -e .        # または `pip install .`（通常インストール）
pj-manager list --json
pj-manager create my-app --json
pj-manager status my-app --json
pj-manager commit my-app -m "wip" --json
pj-manager doctor --json
pj-manager check --json
```

インストールしない場合は、同じ CLI を `PYTHONPATH=src` で実行できます：

```
py -m pj_manager.cli list --json
py -m pj_manager.cli create my-app --json

`--json` を付けると標準出力が JSON 1オブジェクトになり、終了コードは
0（成功）/1（失敗）。対話プロンプトはありません。エージェント向けの
契約（サンドボックス用環境変数 `PJ_MANAGER_DATA_DIR` など）は
[AGENTS.md](AGENTS.md) にあります。

## コントリビュート

Issue・Pull Request 歓迎です。[CONTRIBUTING.md](CONTRIBUTING.md) を見てください。

## ライセンス

MIT License（`LICENSE` ファイル参照）。自由に使って、改変・再配布してかまいません。
