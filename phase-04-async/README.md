# Phase 04（非同期版）— AsyncSessionとpsycopgの非同期API

[Phase 04](../phase-04-alembic/) と同じTask APIを、`create_async_engine()` と `AsyncSession` で書き換えた版です。APIの仕様、Alembicのリビジョン、テストの内容は Phase 04 と同じです。同期版と比べて読むためのサンプルです。

## 起動

```bash
cd phase-04-async
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev
```

接続先の決め方は Phase 04 と同じです。`TASKS_DATABASE_URL`、`DATABASE_URL`（FastAPI CloudのNeon連携が設定する名前）、`sqlite:///./tasks.db` の順に使います。

## 同期版との違い

| 箇所 | Phase 04（同期） | この版（非同期） |
| --- | --- | --- |
| エンジン | `create_engine()` | `create_async_engine()`（`app/db/session.py`） |
| セッション | `Session` | `sqlmodel.ext.asyncio.session.AsyncSession`（`expire_on_commit=False`） |
| リポジトリ・パス操作関数 | `def` | `async def` と `await` |
| ドライバ | psycopg（同期API）、sqlite3 | psycopg（非同期API）、aiosqlite |
| エンジンの後片付け | なし | Lifespanの終了時に `await engine.dispose()` |
| テスト | `TestClient` | `httpx.AsyncClient` と `ASGITransport`、`pytest.mark.anyio` |
| Alembic（`migrations/env.py`） | 同期 | **同期のまま**（下記） |

- 環境変数のURLは `postgresql://...` のままで構いません。`async_database_url()` が `postgresql+psycopg://`（SQLiteは `sqlite+aiosqlite://`）に書き換えてから非同期エンジンに渡します。psycopgはlibpqの接続パラメータをそのまま使うので、Neonの接続文字列に付く `sslmode=require` や `channel_binding=require` も変えずに使えます。
- SQLAlchemy 2.1では、非同期の機能に必要な `greenlet` が自動ではインストールされません。`sqlalchemy[asyncio]` を依存関係に入れています。入れ忘れると `ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed.` になります。
- 非同期のセッションは、属性の遅延読み込みを暗黙には行えません。コミット後に属性を読めなくならないよう、`expire_on_commit=False` にしています。
- psycopg（v3）は同期と非同期の両方のAPIを持つので、マイグレーションは同期のまま同じURLで実行できます。マイグレーションはデプロイ前に1回だけ動くコマンドなので、非同期にしても得はありません。asyncpgのように非同期のAPIしかないドライバを使う場合は、Alembicの非同期テンプレート（`alembic init -t async`）に合わせて `env.py` を書き換えます。

## テスト

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

PostgreSQLでのテストは Phase 04 と同じく、`_test` で終わる名前のDBを用意して実行します。30件のリクエストを同時に送り、コネクションプール（既定は5本＋超過分10本）を超えても順番待ちで処理されることも確かめます。

```bash
docker run -d --rm --name tasks-pg -e POSTGRES_USER=tasks -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=tasks_test -p 5432:5432 postgres:18
TASKS_TEST_POSTGRES_URL=postgresql://tasks:devpass@localhost:5432/tasks_test uv run pytest -q
```

## 同期と非同期の経過時間を比べる（第13章コラム）

`bench/wait_app.py` は、1リクエストごとにPostgreSQLで `SELECT pg_sleep(0.5)` を実行するだけのアプリです。`BENCH_MODE` で `def`（同期）と `async def`（非同期）を切り替えます。`bench/load.py` は、同時に100件のリクエストを送って経過時間を表示します。

```bash
docker run -d --rm --name tasks-pg -e POSTGRES_USER=tasks -e POSTGRES_PASSWORD=devpass \
  -e POSTGRES_DB=tasks -p 5432:5432 postgres:18
export TASKS_DATABASE_URL=postgresql://tasks:devpass@localhost:5432/tasks

# ターミナル1：同期版を起動（非同期版は BENCH_MODE=async）
BENCH_MODE=sync uv run uvicorn bench.wait_app:app --port 8766
# ターミナル2：同時に100件送る
uv run python bench/load.py 100
```

`BENCH_POOL_SIZE=50` を付けると、コネクションプールを50本にします（既定は5本＋超過分10本）。

同期版には、DB接続を `yield` の依存関係から受け取る `/wait-dep` もあります。`load.py` に `--dep` を付けると `/wait-dep` を呼び、`--probe` を付けると負荷をかけている最中の `GET /health` の応答時間も表示します。`BENCH_LIMIT=15` を付けて起動すると、この依存関係に `Depends(max_concurrency=15)` をかけます。

```bash
BENCH_MODE=sync BENCH_LIMIT=15 uv run uvicorn bench.wait_app:app --port 8766
uv run python bench/load.py 100 --dep --probe
```

`BENCH_LIMIT` なしで `/wait-dep` に55件以上を同時に送ると、スレッド（上限40本）と接続（15本）を取り合って止まり、30秒後に `QueuePool limit ... timed out` の500エラーになります。詳しくは第13章のコラムを参照してください。測るときは、同期版と非同期版を同時に起動しないでください。両方の接続がPostgreSQLの同時接続数の上限（既定100）を取り合います。

非同期にしても、1件ずつのクエリが速くなるわけではありません。DBの応答を待つ間に、同じイベントループでほかのリクエストを進められる点が違いです。
