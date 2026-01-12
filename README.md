# bibdb: SQLite-based Bibliography Manager

`bibdb` は、参考文献データを SQLite データベースで一元管理するためのシンプルなコマンドラインツールです。
`.bib` ファイル（BibTeX）をインポートしてマスタデータを作成し、そこから必要な文献だけを抽出したり、重複を整理したりすることができます。

従来の XML ベースの管理システムや巨大な `.bib` ファイル管理からの脱却を目指し、UNIX 哲学（Do one thing and do it well）に基づいて設計されています。

## 特徴

* **SQLite マスタ管理**: 堅牢な SQLite (`~/refs.db`) でデータを管理。
* **Dropbox / クラウド同期対応**: 環境変数により、データベースの場所を自由に設定可能。
* **安全なインポート (Git-like Conflict Resolution)**: 既存データと異なる内容をインポートする際、差分を表示して「上書き(Overwrite)」か「スキップ(Skip)」かを選択できます。
* **重複整理 (Deduplication)**: DOI の一致やタイトルの類似度（Fuzzy matching）に基づいて重複候補を検出し、対話的にマージできます。
* **柔軟なエクスポート**: 全件出力はもちろん、指定した文献キーのリストに基づいた部分出力が可能。Pandoc を使った執筆フローに最適です。

## 必要要件

* Python 3.6+
* [bibtexparser](https://github.com/sciunto-org/python-bibtexparser)

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

`bibdb` はサブコマンド形式 (`import`, `export`, `dedup`) で動作します。

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

## 運用フロー例: Word での論文執筆 (Pandoc連携)

Word で特定のフォーマット（APA, IEEEなど）の文献リストが必要な場合のワークフローです。

1. **文献キーのリスト作成**:
論文で使用する文献IDを `citations.txt` にリストアップします。
2. **BibTeX 生成**:
`bibdb` を使って必要な文献だけの `.bib` を作ります。
```bash
bibdb export -k citations.txt > temp.bib

```


3. **Pandoc で変換**:
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
