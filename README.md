# bibdb: SQLite-based Bibliography Manager

`bibdb` は、参考文献データを SQLite データベースで一元管理するためのシンプルなコマンドラインツールです。
`.bib` ファイル（BibTeX）をインポートしてマスタデータを作成し、そこから必要な文献だけを抽出したり、重複を整理したりすることができます。

巨大な `.bib` ファイル管理からの脱却を目指し、UNIX 哲学（Do one thing and do it well）に基づいて設計されています。

## 特徴

* **安全なインポート (Git-like Conflict Resolution)**: 既存データと異なる内容をインポートする際、差分を表示して「上書き(Overwrite)」か「スキップ(Skip)」かを選択できます。
* **Lossless 重複整理**: 重複エントリをマージする際、片方にしかない独自情報（メモなど）は自動的に移動・統合され、情報は失われません。
* **bibdb 自体は高級な機能を持たない**: `fzf` (文献絞り込みに活用) や `pandoc` (`.bib` 形式の文献情報を word 掲載用に変換) などのツールと連携しやすい出力形式をとっています。

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

* **判定基準**: DOI の完全一致、またはタイトルの類似度。
* **Lossless Merge**:
    * BibTeX情報が重複している場合、片方を残して削除します。
    * **ユーザー独自データ（メモ等）は、削除される側から残す側へ自動的に移動・統合されます。** これにより、マージによって貴重なメモが消えることを防ぎます。

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
* **Cascade Delete**: 文献を削除すると、その文献に紐付いているユーザー独自データ（`extras` テーブル内のメモやパスなど）も**自動的に削除**されます。ゴミデータは残りません。

## ユーザー独自データの管理 (`extras` テーブルの活用)

BibTeX ファイルには含まれない情報（PDFのパス、重要度、メモなど）は、`extras` テーブルで管理します。
`extras` に対するデータの読み込み・編集・書き出し・削除などに関するサブコマンドは一切用意していません。
SQL クエリを活用して編集することを想定しています。

**(例) 文献キーを使ってデータを追加する**

```sql
-- 基本構文:
-- INSERT INTO extras (entry_id, extra_key, extra_value)
-- SELECT id, 'キー', '値' FROM entries WHERE cite_key = '文献キー';

-- 例: 'Ohsu2024' に PDFパスを登録する
INSERT INTO extras (entry_id, extra_key, extra_value)
SELECT id, 'file', '/docs/papers/ohsu2024.pdf' 
FROM entries 
WHERE cite_key = 'Ohsu2024';

-- 例: 'Knuth1984' にメモを追加する
INSERT INTO extras (entry_id, extra_key, extra_value)
SELECT id, 'memo', '必読文献' 
FROM entries 
WHERE cite_key = 'Knuth1984';

```

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
* **extras テーブル**: ユーザー固有の付加情報。`import` の影響を受けず、`dedup` 時には安全にマージされます。

## License

Personal Use / MIT License
