# Cognito access token example

第31章（発展編）の独立サンプルです。既存 Phase 01〜04 には認証を追加しません。

## テスト（AWSアカウント不要）

Python 3.14 / uv を準備し、このディレクトリで実行します。依存バージョンは `uv.lock` で固定しています。

```bash
cd cognito-auth
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest -q
```

テストはローカルで生成したRSA鍵でトークンに署名し、JWKSクライアントを差し替えて実行します。
AWSへの通信や認証情報は不要です。

## 実環境のCognitoで試す場合

```bash
export COGNITO_REGION=ap-northeast-1
export COGNITO_USER_POOL_ID=ap-northeast-1_XXXXXXXXX
export COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
uv run fastapi dev
```

認証済みクライアントから `Authorization: Bearer <access_token>` を送信します。
動作確認用のトークン取得手順は本文の「実際のCognitoで試す」を参照してください。

実環境ではOAuth2 Authorization Code + PKCE、スコープ、トークン寿命、
ログの秘匿化、レート制限、失効と鍵ローテーションを別途検討してください。
このサンプルの `sub` 一致は所有者認可の教材であり、実際のDBのアクセス制御は未実装です。
