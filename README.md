# bibdb: SQLite-based Bibliography Manager

`bibdb` は、参考文献データを SQLite データベースで一元管理するためのシンプルなコマンドラインツールです。
`.bib` ファイル（BibTeX）をインポートしてマスタデータを作成し、そこから必要な文献だけを抽出したり、重複を整理したりすることができます。

巨大な `.bib` ファイル管理からの脱却を目指し、UNIX 哲学（Do one thing and do it well）に基づいて設計されています。

## 特徴

* **安全なインポート (Git-like Conflict Resolution)**: `.bib` ファイルまたは bibdb 互換の `.db` ファイルをインポートできます。既存データと異なる内容がある場合は差分を表示して「上書き(Overwrite)」か「スキップ(Skip)」かを選択できます。
* **Lossless 重複整理**: 重複エントリをマージする際、片方にしかない独自情報（メモ・図表メモなど）は自動的に移動・統合され、情報は失われません。`.db` インポート時も同じ方針で `extras` / `figure_notes` が統合されます。
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

### 複数の DB を使い分ける

プロジェクトごとや共同研究者との共有ディレクトリに別の DB を置く場合は、`$BIBDB_PATH` をその都度上書きします。

**カレントディレクトリの DB を一時的に使う:**

```bash
export BIBDB_PATH=$(realpath project.db)
bibdb list
bibdb import new.bib
```

`realpath` で絶対パスに変換しているため、その後 `cd` で移動しても正しく参照されます。

**シェル関数として登録する（頻繁に使う場合）:**

```bash
# .bashrc / .zshrc に追記
collab() { BIBDB_PATH=/shared/collab/refs.db bibdb "$@"; }
```

```bash
collab list | fzf
collab import new.bib
```

**デフォルト DB に戻すには:**

```bash
unset BIBDB_PATH  # ~/refs.db に戻る
# または
export BIBDB_PATH="$HOME/Dropbox/refs.db"
```

## 使い方

`bibdb` はサブコマンド形式 (`import`, `export`, `dedup`, `list`, `delete`, `set-extra`) で動作します。

### 1. データのインポート (`import`)

`.bib` ファイルまたは bibdb 互換の `.db` ファイルをデータベースに取り込みます。
引数の拡張子で自動判定します。

```bash
bibdb import my_references.bib   # BibTeX ファイルから
bibdb import shared.db           # bibdb 互換 .db ファイルから

```

* **新規エントリ**: 自動的に追加されます。
* **既存エントリ（差分なし）**: fields はスキップします。
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

#### `.db` インポートの追加動作

`.bib` インポートと異なる点が2つあります。

* **`extras` / `figure_notes` の lossless マージ**: fields が差分なし・skip のいずれの場合でも、インポート元の `extras`（タグ・メモ・ファイルリンク等）と `figure_notes`（図表メモの画像・キャプション）が常にマージされます。既存データは削除されません。インポート元 DB に `figure_notes` テーブルが無い（bibweb でこの機能を使う前に作られた古い `.db`）場合は、単にスキップされます。同様に、インポート元 DB の `extras` に `note` カラムが無い（`note` 追加より前に作られた古い `.db`）場合は `note` を `NULL` として扱い、正常にインポートを続行します。
* **`added_at` の保持**: インポート元 DB の登録日時をそのまま引き継ぎます（`.bib` インポートは常に現在時刻になります）。

**典型的なユースケース:**

```bash
# bibweb でエクスポートした .db を自分の DB に取り込む
bibdb import shared.db

# 複数の .db を順番にマージして 1 つの DB に集約する
bibdb import project_a.db
bibdb import project_b.db

```

### 2. データのエクスポート (`export`)

データベースから BibTeX 形式で出力します。

**全件バックアップ:**

```bash
bibdb export > master_backup.bib

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
    * **ユーザー独自データ（メモ・図表メモ等）は、削除される側から残す側へ自動的に移動・統合されます。** これにより、マージによって貴重なメモが消えることを防ぎます。図表メモ（`figure_notes`）の並び順は、残す側の既存メモの後ろに追加される形で再採番されます。

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
* **Cascade Delete**: 文献を削除すると、その文献に紐付いているユーザー独自データ（`extras` テーブル内のメモやパス、`figure_notes` テーブル内の図表メモや画像など）も**自動的に削除**されます。ゴミデータは残りません。

## ユーザー独自データの管理 (`extras` テーブルの活用)

BibTeX ファイルには含まれない情報（PDFのパス、重要度、メモなど）は、`extras` テーブルで管理します。
この設計により、bibdb は「BibTeX の正規管理」と「ユーザーの思考・運用ログ」を明確に分離します。

`extras` の一覧・編集・削除といった一般的な操作に関するサブコマンドは用意していません。SQL クエリを活用することを想定しています。

ただし、標準入力から1件だけ値を書き込む `set-extra` サブコマンドのみ例外的に用意しています。`sqlite3` で直接 `INSERT` しようとすると、複数行や引用符を含むテキスト（Markdown の要約など）はエスケープが煩雑になるため、パイプで値を渡せる書き込み専用のコマンドとして追加しました。

### (例) `set-extra` で Markdown の要約を登録する

```bash
# 標準入力の内容をそのまま md.digest として登録する（末尾の改行は1つだけ除去されます）
some_command | bibdb set-extra Knuth1984 md.digest

# 同じ (cite_key, extra_key) の組がすでに存在する場合はデフォルトではエラーになる
# （誤って上書き・重複させないためのガード）

# --append: 別行として追加する（tags や file のように複数値を持たせたいとき）
echo "must-read" | bibdb set-extra Knuth1984 tags --append

# --replace: 既存の値をすべて削除してから新しい値を1件だけ登録する
some_command | bibdb set-extra Knuth1984 md.digest --replace

# --replace の時点で (cite_key, extra_key) の組がすでに2件以上重複している場合は --force が必要
some_command | bibdb set-extra Knuth1984 md.digest --replace --force

# --note: extras.note に備考を添える（省略時は NULL）
echo "https://www.dropbox.com/scl/fi/xxxx/Knuth1984.pdf" | bibdb set-extra Knuth1984 file --append --note "元論文"
```

詳細は [CLI Reference](#bibdb-set-extra--set-an-extras-value-from-stdin) を参照してください。

### (例) SQL で直接データを追加する（一覧・複数件の一括操作など）

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

### (例) 任意の文献キーの extras を一覧する

コマンドラインのワンライナーだけで完結させることも可能ですが、以下のようなフローにしておくとメンテナンスしやすくなります。

**1. SQL クエリファイルの作成**

例えば `select_extras.sql` という名前で以下の内容を保存します。

```sql
-- select_extras.sql

-- 1. タブ区切りモードに設定（キーにスペースが含まれる場合の対策など）
.mode tabs

-- 2. 一時テーブルを作成
CREATE TEMPORARY TABLE selected_keys (key TEXT);

-- 3. 標準入力 (/dev/stdin) からデータを一時テーブルに流し込む
.import /dev/stdin selected_keys

-- 4. 表示を見やすく整形して出力
.headers on
.mode column
SELECT e.cite_key, x.extra_key, x.extra_value 
FROM extras x 
JOIN entries e ON x.entry_id = e.id 
JOIN selected_keys s ON e.cite_key = s.key;

```

**2. コマンドラインの実行**

パイプラインの最後で `sqlite3` を呼び出す際、ダブルクォートのなかで `.read ファイル名` を指定します。

```bash
[文献キーを抽出する手続き] | sqlite3 $BIBDB_PATH ".read select_extras.sql"

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



# Reference: Database Schema & CLI

## Database Schema (SQLite)

`bibdb` が作成・利用するテーブルは `entries`, `fields`, `extras`, `figure_notes` の4つです。


---

### Table: `entries` (文献の主テーブル)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 内部ID |
| cite_key | TEXT | UNIQUE NOT NULL | CiteKey（例: `Knuth1984`） |
| entry_type | TEXT | NOT NULL | BibTeX の ENTRYTYPE（例: `article`, `book`） |
| added_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 登録日時 |

---

### Table: `fields` (BibTeX フィールド; Key-Value)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 内部ID |
| entry_id | INTEGER | FOREIGN KEY → entries(id) ON DELETE CASCADE | 親エントリ |
| field_key | TEXT | NOT NULL | 例: `title`, `author`, `year`, `doi` |
| field_value | TEXT |  | 値（文字列） |
| (entry_id, field_key) | — | UNIQUE(entry_id, field_key) | **文献ごとに field_key は一意** |

**設計意図**
- `fields` は “BibTeX 的に 1つのキーに 1つの値” を前提にしています。
- `import` で更新されるのは基本的にこの `entries` + `fields` です。

---

### Table: `extras` (ユーザー独自データ; Key-Value)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 内部ID |
| entry_id | INTEGER | FOREIGN KEY → entries(id) ON DELETE CASCADE | 親エントリ |
| extra_key | TEXT | NOT NULL | 例: `memo`, `file`, `tag` |
| extra_value | TEXT |  | 値（文字列） |
| note | TEXT |  | この行についての備考・概要（任意）。複数のファイルリンクや `md.*` を持つ場合に、それぞれの用途を書き添えるためのもの。`bibweb` の Info/Markdown/Extras タブに表示される |
| UNIQUE | — | (なし) | **同じ extra_key を複数持てる** |

**設計意図**
- `extras` は `bibdb` のサブコマンドでは編集しません（SQL で直接操作する運用を想定）。
- `note` は `(extra_key, extra_value)` の組ごとの補足情報という位置づけで、`dedup` / `.db` インポートの重複判定には使いません（後述）。
- `dedup` では **Lossless** に統合されます：
  - 片方にしかない `(extra_key, extra_value)` は移動（同一ペアは重複回避、`note` の差異は無視）
- `delete` では **ON DELETE CASCADE** により、紐づく `fields` / `extras` も削除されます。

---

### Table: `figure_notes` (図表メモ; 画像添付)

実証研究では表・図・数式の読解が本文以上に重要になることが多いため、`bibweb` の「Exhibits」タブ（Info タブと Markdown タブの間）から、論文中の図表のスクリーンショットとメモを直接貼り付けられるようにするための専用テーブルです。
`extras` は値が TEXT のみの key-value テーブルで、画像バイナリ・表示順を自然に表現できないため、`extras` を拡張するのではなく別テーブルとして追加しています。

| Column | Type | Constraints | Notes |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | 内部ID |
| entry_id | INTEGER | NOT NULL, FOREIGN KEY → entries(id) ON DELETE CASCADE | 親エントリ |
| label | TEXT |  | 例: `Fig. 3`, `Table 2`（自由記述） |
| memo | TEXT |  | ユーザーのメモ・解釈 |
| image_data | BLOB |  | 画像本体。bibdb 自体は中身を加工しない（保存されるバイト列の形式は書き込み元次第。`bibweb` は PNG パレット削減のみ行い、リサイズはしない。詳細は [bibweb の README](https://github.com/ugohsu/bibweb) 参照） |
| image_mime | TEXT |  | 例: `image/png` |
| sort_order | INTEGER | NOT NULL DEFAULT 0 | 表示順。`bibweb` の GUI から後から並べ替え可能 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 登録日時 |

**設計意図**
- `figure_notes` も `extras` と同様、`bibdb` のサブコマンドでは編集しません（画像添付は `bibweb` の GUI から行う運用を想定）。
- `dedup` と `.db` インポートでは `extras` と同じ方針で **Lossless** に統合されます（[Table: `extras`](#table-extras-ユーザー独自データ-key-value) 参照）。
- `delete` では **ON DELETE CASCADE** により、紐づく `figure_notes` も削除されます。
- 画像を貼り付けていくと DB ファイルは大きくなっていきます（`bibweb` 側でパレット削減はするがリサイズはしないため）。Dropbox 等で同期している場合は特に注意してください。

---

### 重要ポイント（Unique 制約の違い）

- **`entries.cite_key` は UNIQUE**
  - 文献キー（CiteKey）は DB 全体で一意です。
- **`fields` は (entry_id, field_key) が UNIQUE**
  - **1つの文献（entry_id）につき、同じ field_key は1回しか持てません**（例：`title` は1つだけ）。
- **`extras` には UNIQUE 制約がない**
  - **1つの文献（entry_id）に同じ extra_key を複数持てます**（例：`memo` を複数行で保存、`file` を複数登録、などが可能）。
  - これは「ユーザー独自データを自由に積める」設計です（ただし、重複管理はユーザー側の運用で行います）。
- **`figure_notes` にも UNIQUE 制約がない**
  - 1つの文献に何件でも図表メモを持てます。表示順は `sort_order` で管理し、値自体には一意性を要求しません。

---

## CLI Reference (Arguments)

基本形:

```bash
bibdb <command> [options]
```

サブコマンドは `import`, `export`, `dedup`, `list`, `delete`, `set-extra` です。

---

### `bibdb import` — Import .bib or .db file into DB

```bash
bibdb import <bibfile> [--force|-f]
```

| Arg          | Required | Description               |
| ------------ | -------: | ------------------------- |
| bibfile      |      Yes | 入力 `.bib` または `.db` ファイルパス |
| --force / -f |       No | コンフリクト時の確認をスキップして上書き     |

**挙動メモ**

* 拡張子が `.db` であれば bibdb 互換 DB インポートとして動作し、それ以外は `.bib` インポートとして動作します。
* CiteKey が新規なら `entries` + `fields` + `extras` + `figure_notes` をすべて追加。
* 既存で差分があれば diff を表示して overwrite/skip を選択（`--force` で全 overwrite）。
* **`.db` インポート限定**: overwrite/skip いずれの場合も `extras` / `figure_notes` は常に lossless マージされます。`added_at` はインポート元の値を保持します。インポート元 DB に `figure_notes` テーブルが無ければそこはスキップされ、`extras` に `note` カラムが無ければ `note` を `NULL` として扱います（いずれも古い `.db` との互換性維持）。

---

### `bibdb export` — Export DB entries to BibTeX

```bash
bibdb export [--keys|-k <file>]
# または（stdin）
```

| Arg                | Required | Description               |
| ------------------ | -------: | ------------------------- |
| --keys / -k <file> |       No | CiteKey を1行1件で書いたファイル     |
| stdin              |       No | tty でない場合、stdin からキー列挙を読む |

**優先順位（概念）**

1. `--keys` があればファイルから
2. stdin があれば stdin から
3. それ以外であれば全件

---

### `bibdb dedup` — Find and merge duplicates

```bash
bibdb dedup [--threshold|-t <float>]
```

| Arg              | Required | Default | Description          |
| ---------------- | -------: | ------: | -------------------- |
| --threshold / -t |       No |     0.9 | タイトル類似度しきい値（0.0–1.0） |

**重複判定**

* DOI の完全一致、または
* 正規化タイトル同士の類似度（SequenceMatcher）≥ threshold

**マージ方針（Lossless）**

* `fields`: keep 側に存在しない field_key だけを追加
* `extras`: keep 側に同一 `(extra_key, extra_value)` がないものだけを移動（`note` の差異は判定に使わない）
* `figure_notes`: 削除される側の全メモを keep 側へ付け替え、`sort_order` は keep 側の末尾に再採番

---

### `bibdb list` — List entries for fzf/grep

```bash
bibdb list
```

オプションなし。タブ区切りで次の形式を出力します。

[CiteKey]\t[Title] ([Year]) - [Author]

---

### `bibdb delete` — Delete entries by cite keys

```bash
bibdb delete [KEY1 KEY2 ...] [--keys|-k <file>] [--force|-f]
# または（stdin）
```

| Arg                  | Required | Description                     |
| -------------------- | -------: | ------------------------------- |
| keys_pos (位置引数; 複数可) |       No | 直接キー指定（例: `bibdb delete A B C`） |
| --keys / -k <file>   |       No | キー一覧ファイル（1行1件）                  |
| --force / -f         |       No | 確認なしで削除（非対話環境では推奨）              |
| stdin                |       No | tty でない場合、stdin からキー列挙を読む       |

**削除時の注意**

* `--force` がない場合、削除前に確認プロンプトが出ます。
* ON DELETE CASCADE により、対象 `entries` を消すと、その `fields` / `extras` も同時に削除されます。

---

### `bibdb set-extra` — Set an extras value from stdin

```bash
bibdb set-extra <cite_key> <extra_key> [--append | --replace] [--force|-f] [--note NOTE]
```

| Arg          | Required | Description                                         |
| ------------ | -------: | ---------------------------------------------------- |
| cite_key     |      Yes | 対象の CiteKey                                          |
| extra_key    |      Yes | `extras.extra_key`（例: `md.digest`, `memo`, `tags`）    |
| --append     |       No | 既存行があっても新しい行として追加する（複数値を許容する extra_key 向け）             |
| --replace    |       No | 既存行をすべて削除してから新しい値を1件だけ挿入する                            |
| --force / -f |       No | `--replace` の時点で対象の組が2件以上重複している場合に必須                  |
| --note       |       No | `extras.note` に保存する備考。省略時は `NULL`                     |
| stdin        |      Yes | `extra_value` として保存する内容（末尾の改行は1つだけ除去される）              |

**挙動メモ**

* `cite_key` が存在しない場合はエラーで終了します。
* オプションなしの場合、対象の `(cite_key, extra_key)` の組がすでに1件でも存在すればエラーで終了します（該当件数を表示）。存在しなければ1件挿入します。
* `--append` と `--replace` は同時指定できません。
* `--append` は既存件数に関わらず常に新しい行を1件追加します。
* `--replace` は既存行をすべて削除してから新しい値を1件挿入します。既存が2件以上ある場合は `--force` が無いとエラーで終了します（誤って複数のメモを一括で握りつぶす事故を防ぐため）。
* `--force` は `--replace` と同時に指定しない限りエラーになります。
* `--note` を省略すると `note` は `NULL` になります。`--replace` は行ごと削除してから作り直すため、既存行に備考が付いていても `--note` を指定し直さない限り引き継がれません。

**典型的なユースケース: エージェント型AIによる要約の登録**

```bash
# 要約を生成させ、そのままパイプで登録する（クォートや改行のエスケープを考える必要がない）
claude -p "Knuth1984.pdf を要約して" | bibdb set-extra Knuth1984 md.digest

# 既存の要約を更新する
claude -p "..." | bibdb set-extra Knuth1984 md.digest --replace

# 備考（note）を添えて登録する
claude -p "..." | bibdb set-extra Knuth1984 md.digest --replace --note "研究会報告資料"
```

---

## Environment Variable

| Name       | Meaning                     |
| ---------- | --------------------------- |
| BIBDB_PATH | DB の保存パス（未設定なら `~/refs.db`） |

---


## License

Personal Use / MIT License

