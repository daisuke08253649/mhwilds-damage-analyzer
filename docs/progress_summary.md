## 実装進捗サマリー

最終更新: 2026-07-16

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

### 🔧 作業中・未完了のタスク

- **本番E2Eフローの再確認（Render OOM対応・Gemini OCRタイムアウト対応の両方）が未実施**：どちらの修正も本番マージまでは完了しているが、実際にRenderへの反映と動作確認はまだ行っていない
- Renderのデプロイトリガーが`main`起点か`develop`起点か未確認（前回セッションから継続して未確認）
- Renderの環境変数`GEMINI_MODEL`が明示的に設定されているか未確認（未設定なら新デフォルトの`gemini-3.1-flash-lite`が自動的に使われるはずだが、明示的に`gemma-4-26b-a4b-it`等が設定されている場合は上書きされず、今回の修正の恩恵を受けられない）
- 50分動画でのパフォーマンス・メモリ使用量確認：未着手
- Gemini API消費量モニタリング設定：未着手

### 👉 次のアクション（再開時の起点）

1. Renderのデプロイ設定（デプロイトリガーとなるブランチ）を確認し、今回の2つの修正（`main`の`b01615a`までの内容）がRenderに反映されているか確認する
2. Renderの環境変数`GEMINI_MODEL`の設定値を確認する（未設定 or `gemini-3.1-flash-lite`であることが望ましい。明示的に`gemma-4-26b-a4b-it`になっている場合は用途に応じて見直す）
3. 反映されていれば、本番サイト（https://mhwilds-damage-analyzer.vercel.app）で短いMP4を再度アップロードし、
   - 解析が最後まで完了するか
   - Render Dashboard → Logs に`Gemini OCR timed out`等のエラーが出ていないか
   - Render Dashboard → Metrics でメモリ使用量のピークが以前より下がっているか
   を確認する
4. E2Eが正常に完了した場合：50分動画でのパフォーマンス・メモリ確認、Gemini API消費量モニタリング設定に着手する
5. E2Eでまだ問題が出た場合：Renderのログとブラウザ側のSSEエラーメッセージを確認してから追加調査する

### ⚠️ 懸念事項・確認が必要な点

- 今回`GEMINI_MODEL`の既定値を有料ティアのある`gemini-3.1-flash-lite`に変更したため、利用量次第では無料枠を超えて課金が発生する可能性がある。運用コスト0円方針（`requirements.md` 5.2）と照らして、実際の消費量モニタリングが必要
- `CLAUDE.md`の環境変数一覧に`OPENROUTER_API_KEY`/`OPENROUTER_MODEL`/`OCR_BACKEND=openrouter（デフォルト）`という記載が残っているが、実際のコードはOpenRouter実装を持たず（`OCR_BACKEND`は`gemini`または`finetuned`のみ）、これは過去に一度OpenRouter経由の実装を試した後Geminiへ戻した際の記載漏れと見られる。ドキュメントのドリフトとして別途整理が必要
- Renderの自動デプロイトリガーが`main`か`develop`かが未確認のため、次回再開時に最初に確認する必要がある
- develop→mainの昇格は過去の履歴（`Merge branch 'develop'`コミット）に倣い、PRを介さず直接`git merge`で実施している。この運用を続けるかは今後も要確認
- Render 無料プランは15分アクセスがないとスリープする問題は引き続き未解決（許容する方針）。初回アクセス時にコールドスタート待ちが発生し得る
- ローカルでの Supabase 起動不可の問題（Windows/Docker のポートbinding衝突）は継続中。新規マイグレーション追加時は `supabase db reset` でのローカル検証ができないため、SQL構文を目視で慎重に確認する必要がある
- YouTube URL機能はフロントエンドから非表示にしたままだが、バックエンドの`POST /api/v1/upload/youtube`エンドポイントは残存（Cookie認証の仕組みは実装済み）
