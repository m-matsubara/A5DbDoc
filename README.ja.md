# a5dbdoc

データベースのスキーマ定義（DDL）を Markdown ファイルとして出力する CLI ツールです。
生成したファイルを Claude Code などの LLM に渡すことで、正確な SQL を書いてもらいやすくなります。

SQLAlchemy が対応するすべてのデータベース（PostgreSQL, MySQL, SQLite, SQL Server, Oracle など）に対応しています。

[English](README.md)

## インストール

```bash
pip install -e .
```

データベースドライバは別途インストールしてください。

```bash
pip install -e ".[pg]"      # PostgreSQL (psycopg2)
pip install -e ".[mysql]"   # MySQL (PyMySQL)
pip install -e ".[mssql]"   # SQL Server (pyodbc)
pip install -e ".[oracle]"  # Oracle (cx_Oracle)
```

## 使い方

### スキーマを Markdown にエクスポート

```bash
a5dbdoc export <接続URL>
```

```bash
# SQLite
a5dbdoc export sqlite:///./myapp.db

# PostgreSQL
a5dbdoc export postgresql://user:pass@localhost/mydb

# MySQL
a5dbdoc export mysql+pymysql://user:pass@localhost/mydb

# SQL Server
a5dbdoc export "mssql+pyodbc://user:pass@server/mydb?driver=ODBC+Driver+17+for+SQL+Server"

# 出力先を指定
a5dbdoc export sqlite:///./myapp.db --output ./llm-context/

# スキーマを指定（PostgreSQL など）
a5dbdoc export postgresql://user:pass@localhost/mydb --schema public

# テーブル名で絞り込み（glob パターン）
a5dbdoc export postgresql://user:pass@localhost/mydb --table "order*" --table "customer*"

# テーブルごとに別ファイルに分割
a5dbdoc export postgresql://user:pass@localhost/mydb --split
```

**オプション一覧:**

| オプション | 短縮 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `--output` | `-o` | `./docs/schema` | 出力先ディレクトリ |
| `--schema` | `-s` | (全スキーマ) | 対象スキーマ名。複数指定可 |
| `--table` | `-t` | (全テーブル) | テーブル名の glob パターン。複数指定可 |
| `--split` | | false | テーブルごとに別ファイルに出力 |
| `--no-index` | | false | インデックスファイルを生成しない（`--split` 時のみ有効） |

### スキーマ一覧を確認

```bash
a5dbdoc list-schemas postgresql://user:pass@localhost/mydb
```

### テーブル一覧を確認

```bash
a5dbdoc list-tables postgresql://user:pass@localhost/mydb --schema public
```

## 出力形式

`export` を実行すると常に2種類のファイルが生成されます。

1. **`./DB_LAYOUT.md`** — プロジェクトルートに置かれる全テーブルの DDL 概要
2. **`./docs/schema/`** — スキーマ単位（または `--split` でテーブル単位）の詳細ファイル

### スキーマ単位（デフォルト）

スキーマ内のすべてのテーブルを1ファイルにまとめます。

```
docs/schema/
└── public.md
```

### テーブル単位（`--split`）

テーブルごとに個別ファイルとインデックスファイルを生成します。

```
docs/schema/
├── public__index.md
├── public__customers.md
├── public__orders.md
└── public__order_items.md
```

### 出力内容の例

````markdown
# Schema: `public`

- **Database:** PostgreSQL 15.3
- **Tables:** 2
- **Exported:** 2026-04-04

---

```sql
CREATE TABLE public.customers (
    id     INTEGER       NOT NULL,
    name   VARCHAR(120)  NOT NULL,
    email  VARCHAR(255)  NOT NULL,
    CONSTRAINT pk_customers PRIMARY KEY (id),
    CONSTRAINT uq_customers_email UNIQUE (email)
);

CREATE TABLE public.orders (
    id            INTEGER         NOT NULL,
    customer_id   INTEGER         NOT NULL,
    status        VARCHAR(32)     NOT NULL  DEFAULT 'pending',
    total_amount  NUMERIC(12, 2)  NOT NULL,
    notes         TEXT,  -- 備考
    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT fk_orders_customer FOREIGN KEY (customer_id)
        REFERENCES public.customers (id)
);

CREATE INDEX ix_orders_customer_id ON public.orders (customer_id);
```
````

## Claude Code での使い方

プロジェクトルートで `a5dbdoc export` を実行すると `DB_LAYOUT.md` が生成されます。`CLAUDE.md` に記載しておくと Claude Code が常に参照します。

```bash
# スキーマ情報を生成
a5dbdoc export postgresql://user:pass@localhost/mydb \
    --schema public \
    --output ./docs/schema/

# Claude Code で参照
# @DB_LAYOUT.md  または  @docs/schema/public.md
```

プロジェクトの `CLAUDE.md` に以下を追記しておくと、Claude Code が常にスキーマを把握した状態になります。

```markdown
## データベーススキーマ

スキーマ定義は `DB_LAYOUT.md`（概要）と `docs/schema/`（詳細）に格納されています。
SQL を書く際は必ずこれらのファイルを参照してください。
```

## 開発・テスト

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## 接続 URL について

パスワードに `@` や `#` などの特殊文字が含まれる場合は URL エンコードしてください。

```
# @ → %40
postgresql://user:p%40ssword@localhost/mydb
```

SQLAlchemy の接続 URL 形式の詳細は [SQLAlchemy ドキュメント](https://docs.sqlalchemy.org/en/20/core/engines.html) を参照してください。
