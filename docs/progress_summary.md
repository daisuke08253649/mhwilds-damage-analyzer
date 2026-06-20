# 実装進捗サマリー

最終更新: 2026-06-20

---

## ✅ 完了済みのタスク

### Phase 0 — 環境構築・基盤整備
- モノレポ構成でリポジトリ作成（`frontend/` / `backend/` / `supabase/`）
- Next.js・FastAPI プロジェクト初期化、`.env.example` 整備
- Supabase ローカル環境構築、Cloudflare R2 バケット作成

### Phase 1 — データベース構築
- `analysis_sessions` / `damage_logs` テーブル DDL・インデックス作成
- RLS ポリシー設定（`auth.uid() = user_id`）
- マイグレーション `20250401000000`〜`20250401000002` 作成済み

### Phase 2 — バックエンド実装
- 全モジュール実装済み（config / security / supabase / r2 / video / ocr / aggregator）
- 全 API エンドポイント実装済み（upload / analysis / results / history）
- バックグラウンド処理フロー完成

### Phase 3 — フロントエンド実装
- 全ページ・コンポーネント実装済み（`/` / `/analysis/[sessionId]` / `/auth/*` / `/history`）
- SSE カスタムフック・ライブラリ実装済み

### Phase 4 — デプロイ・本番設定（完了）
- Supabase 本番プロジェクト作成・`supabase db push` で本番 DB にマイグレーション適用済み
- Render（バックエンド）デプロイ済み
  - URL: https://mhwilds-damage-analyzer.onrender.com
- Vercel（フロントエンド）デプロイ済み
  - URL: https://mhwilds-damage-analyzer.vercel.app

### Phase 5 — テスト・バグ修正
- ユニットテスト 26 件全パス確認済み
- 本番環境 E2E 確認中に発生したバグを順次修正済み

#### 本番環境で修正したバグ（〜2026-06-17）

| # | 症状 | 原因 | 修正内容 |
|---|---|---|---|
| 1 | CORS エラー | `ALLOWED_ORIGINS` 末尾に `/` がついていた | Render 環境変数から末尾スラッシュを削除 |
| 2 | 500エラー（Supabase） | `SUPABASE_URL` に `/rest/v1` が含まれ二重パスになっていた | Render 環境変数をホスト名のみに修正 |
| 3 | yt-dlp に Node.js が必要 | Dockerfile に Node.js が未インストール | `nodejs` パッケージを Dockerfile に追加 |
| 4 | yt-dlp が Node.js を認識しない | Debian では `nodejs` バイナリ名が `node` でない | Dockerfile に `node` → `nodejs` シンボリックリンク追加、`--js-runtimes node:/usr/bin/nodejs` 指定 |
| 5 | stderr ログが途中で切れる | `stderr_text[:300]` で切り捨てていた | 上限を 2000 文字に拡張 |

#### 本番環境で修正したバグ（2026-06-20）

| # | 症状 | 原因 | 修正内容 |
|---|---|---|---|
| 6 | YouTube URL 機能が動作しない | Render の IP を YouTube がボットとみなしブロック | YouTube URL 入力欄をフロントエンドから非表示に（`page.tsx` から `VideoUrlInput` を削除） |
| 7 | SSE が途中で無音になりエラーが表示されない | OCR API 呼び出し（`generate_content`）にタイムアウトがなくバックグラウンドタスクが無期限ブロック | 30 秒タイムアウトを追加・リトライ処理に組み込み |
| 8 | `CancelledError` 発生時にエラー SSE が送信されない | `except Exception` が `BaseException` をキャッチしない | `except BaseException` に変更し、エラーイベント送信後に `raise` で再スロー |
| 9 | Render のリバースプロキシが SSE 接続を切断する | アイドル状態の HTTP 接続が一定時間でタイムアウト | SSE ハートビート（30 秒ごとに `comment` 送信）を追加。合計 1800 秒でタイムアウトエラーを送信 |

---

## 🔧 作業中・未完了のタスク

### ファイルアップロードの E2E フロー確認（未実施）

- https://mhwilds-damage-analyzer.vercel.app で短い動画ファイル（MP4）をアップロードして解析完了まで確認する
- 2026-06-20 の SSE 安定化修正がデプロイ済みの状態で確認すること

### その他 Phase 5 残タスク

- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

1. **ファイルアップロードの E2E フローを確認する**
   - https://mhwilds-damage-analyzer.vercel.app で短い MP4 をアップロード
   - 解析中にダメージログがリアルタイムで流れ、完了後にサマリーが表示されるか確認
   - Render のログ（Dashboard → Logs）も同時に確認し、エラーが出ていないか見る

2. **E2E が正常に動いた場合**
   - 50 分動画でのメモリ・処理時間を確認
   - Gemini API 消費量のモニタリング設定

3. **E2E でエラーが出た場合**
   - Render のログと SSE のエラーメッセージを確認してから対処

---

## ⚠️ 懸念事項・確認が必要な点

- **Render 無料プランのスリープ**: 15 分間リクエストがないとスリープする。初回リクエスト時に起動まで数十秒かかる
- **Gemini API 無料枠**: 長時間動画では消費量が大きくなる可能性がある。`GEMINI_MODEL` 環境変数で別モデルに切り替え可能
- **OCR タイムアウト（30 秒）の妥当性**: Gemini API のレスポンスが安定して 30 秒以内に返るか未確認。動画によっては頻繁にリトライが発生する可能性がある。問題が続く場合はタイムアウト値を調整する
- **YouTube URL 機能**: フロントエンドから非表示にしたが、バックエンドの `POST /api/v1/upload/youtube` エンドポイントは残存している。API を直接叩けば利用可能な状態。将来的に対応する場合は Cookie 認証（`YOUTUBE_COOKIES_B64`）の仕組みを実装済み
- **Supabase 本番 RLS**: ダッシュボードで RLS が有効になっているか目視確認を推奨
