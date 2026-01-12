# bibdb: SQLite-based Bibliography Manager

`bibdb` は、参考文献データを SQLite データベースで一元管理するためのシンプルなコマンドラインツールです。
`.bib` ファイル（BibTeX）をインポートしてマスタデータを作成し、そこから必要な文献だけを抽出したり、重複を整理したりすることができます。

巨大な `.bib` ファイル管理からの脱却を目指し、UNIX 哲学（Do one thing and do it well）に基づいて設計されています。

## 特徴

* **SQLite マスタ管理**: 堅牢な SQLite (`~/refs.db`) でデータを管理。
* **Dropbox / クラウド同期対応**: 環境変数により、データベースの場所を自由に設定可能。
* **安全なインポート (Git-like Conflict Resolution)**: 既存データと異なる内容をインポートする際、差分を表示して「上書き(Overwrite)」か「スキップ(Skip)」かを選択できます。
* **重複整理 (Deduplication)**: DOI の一致やタイトルの類似度（Fuzzy matching）に基づいて重複候補を検出し、対話的にマージできます。
* **強力なリスト選択 (fzf連携)**: 文献一覧をタブ区切りで出力し、`fzf` 等のツールとパイプで繋ぐことで、高速に文献を検索・選択できます。
* **柔軟なエクスポート**: 全件出力はもちろん、指定した文献キーのリストに基づいた部分出力が可能。Pandoc を使った執筆フローに最適です。

## 必要要件

* Python 3.6+
* [bibtexparser](https://github.com/sciunto-org/python-bibtexparser)
* 推奨ツール: `fzf` (コマンドラインでの絞り込み選択に便利です)

## インストール

1. 依存ライブラリをインストールします。
```bash
pip install bibtexparser

```


2. スクリプトをパスの通ったディレクトリ（例: `~/bin` や `~/local/bin`）に配置し、実行権限を与えます。
```bash
cp bibdb.py ~/bin/bibdb
chmod +x ~/bin/bibdb

```

## 設定（データベースの場所）

デフォルトでは `~/refs.db` にデータベースが作成されます。
Dropbox 等で同期したい場合は、環境変数 `BIBDB_PATH` で場所を指定できます。

**設定例 (`.bashrc` または `.zshrc`)**:

```bash
# BibDB Database Path
export BIBDB_PATH="$HOME/Dropbox/refs.db"

```

設定後、シェルを再読み込みすれば `bibdb` は自動的にそのパスを参照します。

## 使い方

`bibdb` はサブコマンド形式 (`import`, `export`, `dedup`, `list`, `delete`) で動作します。

### 1. データのインポート (`import`)

`.bib` ファイルをデータベースに取り込みます。

```bash
bibdb import my_references.bib

```

* **新規エントリ**: 自動的に追加されます。
* **既存エントリ（差分なし）**: 何もしません（IDは維持されます）。
* **既存エントリ（差分あり）**: コンフリクトが検知され、Diff が表示されます。

**コンフリクト解消の例:**

```text
--- Conflict detected: Ohsu2024 ---
Key: year
  - DB : 2023
  + New: 2024
Action? [o]verwrite / [s]kip : 

```

* `--force` または `-f` オプションを付けると、確認なしですべて上書きします。

### 2. データのエクスポート (`export`)

データベースから BibTeX 形式で出力します。

**全件バックアップ:**

```bash
bibdb export --all > master_backup.bib

```

**特定の文献のみ出力（論文執筆用）:**

引用したい文献キー（Cite Key）を列挙したテキストファイルを用意し、それに基づいて出力します。

```bash
# keys.txt の中身:
# Ohsu2024
# Knuth1984

bibdb export --keys keys.txt > paper.bib

```

パイプ入力にも対応しています：

```bash
cat keys.txt | bibdb export > paper.bib

```

### 3. 重複の整理 (`dedup`)

データベース内の重複エントリを検出し、マージ（名寄せ）を行います。

```bash
bibdb dedup

```

* **判定基準**: DOI の完全一致、またはタイトルの類似度（デフォルト 90%以上）。
* **マージ挙動**: 片方を残し（Keep）、もう片方を削除します。削除される側にしか存在しないフィールド情報は、残す側に自動的にコピーされます。

**オプション:**

* `--threshold <0.0-1.0>`: タイトル類似度のしきい値を変更します（例: `-t 0.8`）。

### 4. 文献の一覧と活用 (`list`)

データベース内の文献を、UNIX ツールで処理しやすい形式（タブ区切り）で一覧表示します。
`fzf` (fuzzy finder) や `grep` と組み合わせることで、強力な検索・選択が可能になります。

```bash
bibdb list
# 出力形式: [CiteKey] \t [Title] ([Year]) - [Author]
# 例:
# Ohsu2024    Analysis of Big Data (2024) - Yuji Ohsu
# Knuth1984   Literate Programming (1984) - Donald E. Knuth

```

**活用例: `fzf` を使ったインタラクティブな文献選択**

`fzf` で文献を絞り込み・複数選択（Tabキー）し、選択した文献だけの `.bib` ファイルを生成できます。

```bash
# リスト表示 -> fzfで選択 -> キー抽出 -> export
bibdb list | fzf -m | awk '{print $1}' | bibdb export > selected.bib

```

### 5. データの削除 (`delete`)

指定した文献キー（Cite Key）を持つエントリをデータベースから削除します。

**キーを直接指定:**

コマンドライン引数でキーを指定して削除します。

```bash
bibdb delete Ohsu2024
# 複数指定も可能です
bibdb delete Ohsu2024 Knuth1984

```

**リストファイルから削除:**

キーが列挙されたテキストファイルを指定して一括削除します。

```bash
bibdb delete --keys delete_list.txt

```

**パイプ連携 (fzf 等):**

`list` コマンドや `fzf` と組み合わせることで、インタラクティブに選択して削除できます。

```bash
# fzf で選択した文献を削除
bibdb list | fzf -m | awk '{print $1}' | bibdb delete

```

* **確認メッセージ**: デフォルトでは削除前に確認プロンプト (`Proceed? [y/N]`) が表示されます。
* `--force` または `-f` オプションを付けると、確認なしで即座に削除します。

## 運用フロー例: Word での論文執筆 (Pandoc連携)

Word で特定のフォーマット（APA, IEEEなど）の文献リストが必要な場合のワークフローです。

1. **文献の選択**:
`fzf` などを使い、必要な文献を選んで一時ファイルに出力します。
```bash
bibdb list | fzf -m | awk '{print $1}' | bibdb export > temp.bib

```


2. **Pandoc で変換**:
Pandoc と CSL (Citation Style Language) を使って Word ファイルを生成します。
```bash
# input.md には "--- nocite: '@*' ... ---" などを記述
pandoc input.md --bibliography=temp.bib --csl=apa.csl -o reference_list.docx

```



## データベース構造

データは SQLite ファイル (`refs.db`) に保存されます。
`sqlite3` コマンドで直接参照・操作することも可能です。

* **entries テーブル**: 文献IDとタイプ (`article`, `book` 等) を管理。
* **fields テーブル**: 文献ごとの詳細フィールド (`author`, `title`, `yomi` 等) を Key-Value 形式で保存。

```sql
-- 例: 日本語の読み(yomi)がある文献を探す
SELECT e.cite_key, f.field_value 
FROM entries e 
JOIN fields f ON e.id = f.entry_id 
WHERE f.field_key = 'yomi';

```

## License

Personal Use / MIT License
