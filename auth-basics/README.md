# Auth basics: API key / OAuth2 password flow

第20章「認証・認可とAPIキーの注意点」の独立サンプルです。既存の Phase 01〜04 には認証を追加しません。

| ファイル | 内容 |
|---|---|
| `api_key_app.py` | `APIKeyHeader` で `X-API-Key` を受け取り、発行済みキーと照合する |
| `oauth2_app.py` | `OAuth2PasswordBearer` と `/token` によるパスワードフロー。トークンはメモリに保存するランダムな文字列 |
| `tasks.py` | 2つのアプリで共有するタスクのデータと、所有者による認可（403/404） |

## テスト

Python 3.14 / uv を準備し、リポジトリのルートから実行します。

```bash
cd auth-basics
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

## 起動して Swagger UI で試す

キーとパスワードは推測されにくいランダムな値を使い、コードやGitに書かないでください。

```bash
# APIキーの例
export API_KEYS="alice=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))'),bob=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
echo "$API_KEYS"
uv run fastapi dev api_key_app.py
```

```bash
# OAuth2パスワードフローの例（別のターミナルで、ポートを分ける）
export DEMO_PASSWORDS="alice=$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))'),bob=$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
echo "$DEMO_PASSWORDS"
uv run fastapi dev oauth2_app.py --port 8001
```

`http://127.0.0.1:8000/docs`（または `:8001/docs`）を開き、右上の **Authorize** ボタンから認証情報を入力します。

このサンプルは学習用です。実際のサービスでは、キーやパスワードのハッシュをDBで管理し、
失効・ローテーション・レート制限・監査ログを設計してください。JWTによる検証は第34章のサンプルで扱います。
