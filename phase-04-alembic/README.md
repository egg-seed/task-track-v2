# Phase 04 — AlembicによるDBスキーマのバージョン管理

Phase 03のTask APIを引き継ぎ、テーブル作成をアプリ起動時の `create_all()` からAlembicへ移します。

## 起動

```bash
cd phase-04-alembic
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev
```

`uv run alembic current` で適用済みリビジョンを確認できます。APIは従来のCRUDに加えて `priority`（0〜5、既定値0）を受け取ります。

## 2段階の履歴

- `0001_create_tasks.py`：Phase 03と同じTaskテーブルを作成
- `0002_add_task_priority.py`：既存データを消さずに `priority` を追加、未設定の既存行を0にする

手順は `uv run alembic upgrade head`。直前のスキーマを検証する場合は `uv run alembic downgrade 0001` を使用します。ただし実運用環境では事前バックアップと手順確認が必須です。

設定は `app/config.py` の `Settings`（pydantic-settings）が、環境変数と `.env` ファイルから読みます（第26章）。FastAPI本体とAlembicは同じ設定を使います。

| 環境変数 | 既定値 | 内容 |
| --- | --- | --- |
| `TASKS_ENV` | `development` | `development`・`test`・`production`。`production` では、サーバーのDBが設定されていないと起動しない |
| `TASKS_DATABASE_URL` | なし（`sqlite:///./tasks.db`） | DBの接続先。未設定なら `DATABASE_URL`（FastAPI CloudのNeon連携が設定する名前）を読む |
| `TASKS_LOG_LEVEL` | `INFO` | `DEBUG`・`INFO`・`WARNING`・`ERROR`・`CRITICAL` |
| `TASKS_CORS_ORIGINS` | `["http://localhost:5173", "http://127.0.0.1:5173"]` | ブラウザーからAPIを呼んでよいオリジン（JSONの配列）。既定はカンバン画面（`frontend/`）の開発用URL |

手元で `.env` を使う場合は `cp .env.example .env` で作ります。`.env` はGit、Docker、`fastapi deploy` のいずれにも含まれません。環境変数を設定した場合は、`.env` より環境変数が優先されます。テストは実ファイルのSQLiteをテストごとに作成し、Alembicで初期化します。

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

## PostgreSQLで試す（第29章）

`psycopg`（v3）を依存関係に含めているので、`TASKS_DATABASE_URL` に `postgresql://` で始まるURLを指定するとPostgreSQLに接続します。Dockerで試す例です。

```bash
docker run -d --rm --name tasks-pg -e POSTGRES_USER=tasks -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=tasks -p 5432:5432 postgres:18
export TASKS_DATABASE_URL=postgresql://tasks:devpass@localhost:5432/tasks
uv run alembic upgrade head
uv run fastapi dev
```

PostgreSQLでのマイグレーションとAPIのテストは、`_test` で終わる名前のDBを用意して実行します。テストはDBの中身を毎回消すので、ほかの名前のDBは拒否します。

```bash
docker exec tasks-pg psql -U tasks -c 'CREATE DATABASE tasks_test'
TASKS_TEST_POSTGRES_URL=postgresql://tasks:devpass@localhost:5432/tasks_test uv run pytest -q
```

## ログとヘルスチェック（第31章）

`app/observability.py` は、標準ライブラリだけで次のことを行います。

- リクエストごとに、1行のJSONログ（`app.request`）を標準出力に書く。項目は `request_id`、`method`、`route`（`/tasks/{task_id}` のようなテンプレート）、`status_code`、`duration_ms`
- レスポンスに `X-Request-ID` ヘッダーを付ける。リクエストの `X-Request-ID` は、英数字と `._-` だけの64文字以内なら引き継ぎ、それ以外はサーバーで生成する
- 想定外の例外は、トレースバックをログに残し、利用者には `{"detail": "Internal Server Error", "request_id": "..."}` だけを返す
- ヘッダー、クエリ文字列、リクエスト本文はログに書かない。クエリ文字列を含むUvicornのアクセスログは止める

ヘルスチェックは2つあります。

| パス | 確かめること | DBが止まっているとき |
| --- | --- | --- |
| `/health` | プロセスが応答するか（liveness） | 200 |
| `/health/ready` | DBに `SELECT 1` を実行できるか（readiness） | 503 |

ログレベルは `TASKS_LOG_LEVEL`（既定は `INFO`）で変えられます。

## 本番向けのコンテナで動かす（第27章）

`Dockerfile` は本番を想定した構成です。

- 2段階のビルド：ビルド用の段階でuvを使って仮想環境を作り、実行用の段階には仮想環境とコードだけをコピーする（uvとそのキャッシュは実行用イメージに入らない）
- 仮想環境とコードを別のレイヤーにする：コードを変えても、約140MBの仮想環境のレイヤーは作り直さない
- root以外のユーザー（UID 10001）で実行する
- `CMD` をexec形式で書き、`docker stop` のSIGTERMをFastAPIが直接受け取って終了する
- `HEALTHCHECK` で `/health`（liveness）を確かめる

`compose.yaml` は、PostgreSQL、マイグレーション（1回だけ実行して終了）、APIの3つのサービスを手元で動かします。パスワードは手元の実験専用です。

```bash
docker compose up --build -d
curl http://127.0.0.1:8000/health/ready
docker compose down -v   # データのボリュームも削除する
```

手元の8000番が使用中なら、`TASKS_PORT=8001 docker compose up --build -d` のようにポートを変えます。

`migrations/versions` のリビジョンは手動検証済みのコードとして保存しています。自動生成された変更は、適用前に必ずレビューします。フェーズは教育用サンプルであり、運用DBのバックアップ・復元や無停止変更を保証するものではありません。
