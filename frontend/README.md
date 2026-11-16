# カンバン画面

タスク管理API（Phase 04）を呼び出す、ビルド不要の画面です。HTML・CSS・JavaScriptの3ファイルだけで、ライブラリは使っていません。

タスクの作成、状態の移動（`TODO` → `DOING` → `DONE`）、削除ができます。入力の検証やデータの保存は、すべてAPI側で行います。

## 動かし方

ターミナルを2つ使います。

```bash
# ターミナル1：API（http://127.0.0.1:8000）
cd phase-04-alembic
uv sync --locked
uv run alembic upgrade head
uv run fastapi dev

# ターミナル2：画面（http://localhost:5173）
cd frontend
uv run python -m http.server 5173
```

ブラウザーで `http://localhost:5173` を開きます。

画面（5173番ポート）とAPI（8000番ポート）はオリジンが違うので、APIは画面のオリジンをCORSで許可しています。許可するオリジンは、Phase 04の環境変数 `TASKS_CORS_ORIGINS` で変えられます（書籍の第18章）。

APIのURLを変えるときは、`http://localhost:5173/?api=http://127.0.0.1:8001` のように `api` パラメーターで指定します。
