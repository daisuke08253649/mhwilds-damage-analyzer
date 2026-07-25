## 実装進捗サマリー

最終更新: 2026-07-25

### ✅ 完了済みのタスク

`tasks.md` の Phase 0〜4 は全項目完了。Phase 5（テスト・品質保証）はユニットテストと本番バグ修正まで完了。

- **Phase 0〜4**: モノレポ構成・DB/RLS・バックエンド全機能・フロントエンド全画面・Vercel/Render/Supabase本番デプロイ、すべて完了済み
  - Render: https://mhwilds-damage-analyzer.onrender.com
  - Vercel: https://mhwilds-damage-analyzer.vercel.app
- **Phase 5（進行中）**:
  - ユニットテスト全パス確認済み（backend: 56件）
  - 本番環境で発生した各種バグ（CORS、Supabase接続、yt-dlp/Node.js、SSE安定性等）は順次修正済み
- **Supabase 非アクティブ停止対策**（2026-07-14 完了・動作確認済み）
  - GAS から Supabase REST API (PostgREST) に直接 INSERT する `keep_alive_pings` テーブル方式に変更・動作確認済み
- **Render本番環境のOOM対策**（2026-07-14 実装・develop/mainへマージ済み）
  - OCR前にフレームを縮小（`FRAME_MAX_WIDTH`環境変数、デフォルト1280px）してメモリ使用量を削減
  - PR #11（`fix/render-oom-frame-memory` → `develop`）をマージ → `develop`を`main`にマージ・push済み
- **Gemini OCR タイムアウト不具合の修正**（2026-07-16 実装・Codexレビュー3ラウンド対応済み・develop/mainへマージ済み）
  - 本番で「Gemini OCR timed out after 3 attempts」により解析セッションが失敗する不具合が発生
  - 原因調査の過程で `GEMINI_MODEL` の既定値が `gemma-4-26b-a4b-it`（Gemini API経由で使える実在のGemma4モデルだが、無料ティア専用でレート制限が非公開）になっていたことを確認。有料ティアがありレート制限が公式に明記されている `gemini-3.1-flash-lite` を新しい既定値に変更（`GEMINI_MODEL`環境変数で`gemma-4-26b-a4b-it`を指定すればローカルの無料枠テスト用として引き続き使用可能）
  - `asyncio.wait_for`だけに頼っていたタイムアウト制御を見直し、`genai.Client`の`HttpOptions.timeout`で実際のHTTPリクエストを打ち切るよう修正（従来はタイムアウト後もリクエストが裏でスレッドとして動き続け、リトライのたびに積み上がりRenderの限られたCPU/ネットワークを圧迫していた）
  - `GEMINI_OCR_TIMEOUT_SECONDS`環境変数を追加（未設定時45秒、運用上の下限1秒、NaN/inf/極小値はバリデーションで拒否）
  - `httpx.TimeoutException`を正規化し、SDKの生エラーがSSEにそのまま露出しないよう修正。`google-genai`のバージョンを`>=2.0.1,<3.0.0`に固定
  - テストを18件追加（config・OCRサービスのタイムアウト境界値・SDK呼び出し引数の検証など）、計56件全てパス
  - PR #12（`fix/gemini-ocr-timeout` → `develop`）をマージ → `develop`を`main`にマージ・push済み（`main`は`b01615a`まで反映）
- **CLAUDE.mdのGitワークフロー記載を修正**
  - 「PRは`main`ではなく`develop`をターゲットにする」「develop→mainの昇格は最終テスト後に行う」という想定フローに合わせて記載を修正済み
- **本番E2Eフロー確認完了（2026-07-25）**
  - Renderのデプロイトリガーは`main`起点であることを確認（`main`は`b01615a`まで反映済みでOOM対策・タイムアウト修正の両方が本番に載っている）
  - Renderの環境変数`GEMINI_MODEL`が`gemma-4-26b-a4b-it`に明示設定されたままだったのを`gemini-3.1-flash-lite`に変更・再デプロイ
  - 再デプロイ直後の1回目のアップロード試行はSSEストリームが503を返し「サーバーとの接続が切断されました」エラーになったが、再デプロイ直後のコールドスタート性のものと考えられ、少し時間を置いて手動で再アップロードしたところ成功
  - 成功時のRender Metricsでのメモリ使用量ピークは338MB（Render無料プランの512MB枠内に収まっている）、Logsに`Gemini OCR timed out`等のエラーは出ていないことを確認

### 🔧 作業中・未完了のタスク

- Gemini API消費量モニタリング設定：Google Cloud Console側での予算アラート設定を案内済み、ユーザー側での設定作業待ち（`gemini-3.1-flash-lite`は有料ティアありのため、無料枠超過時の課金リスクを踏まえて優先度高め）

### 👉 次のアクション（再開時の起点）

1. Gemini API消費量モニタリング設定の完了確認（Google Cloud Console →「お支払い」→「予算とアラート」でユーザーが設定）

### 📝 スコープ外と判断した項目

- 50分動画でのパフォーマンス・メモリ使用量確認：ユーザー判断により対応不要と決定（2026-07-25）

### ⚠️ 懸念事項・確認が必要な点

- Render本番の`GEMINI_MODEL`を`gemini-3.1-flash-lite`（有料ティアあり）に変更したため、利用量次第では無料枠を超えて課金が発生する可能性がある。運用コスト0円方針（`requirements.md` 5.2）と照らして、実際の消費量モニタリングが必要（次のアクション1番）
- `CLAUDE.md`の環境変数一覧に`OPENROUTER_API_KEY`/`OPENROUTER_MODEL`/`OCR_BACKEND=openrouter（デフォルト）`という記載が残っているが、実際のコードはOpenRouter実装を持たず（`OCR_BACKEND`は`gemini`または`finetuned`のみ）、これは過去に一度OpenRouter経由の実装を試した後Geminiへ戻した際の記載漏れと見られる。ドキュメントのドリフトとして別途整理が必要
- Renderのデプロイトリガーは`main`起点であることを確認済み（2026-07-25）
- develop→mainの昇格は過去の履歴（`Merge branch 'develop'`コミット）に倣い、PRを介さず直接`git merge`で実施している。この運用を続けるかは今後も要確認
- Render 無料プランは15分アクセスがないとスリープする問題は引き続き未解決（許容する方針）。初回アクセス時にコールドスタート待ちが発生し得る
- ローカルでの Supabase 起動不可の問題（Windows/Docker のポートbinding衝突）は継続中。新規マイグレーション追加時は `supabase db reset` でのローカル検証ができないため、SQL構文を目視で慎重に確認する必要がある
- YouTube URL機能はフロントエンドから非表示にしたままだが、バックエンドの`POST /api/v1/upload/youtube`エンドポイントは残存（Cookie認証の仕組みは実装済み）
