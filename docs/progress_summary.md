# 実装進捗サマリー

最終更新: 2026-05-14

---

## ✅ 完了済みのタスク

### Phase 0 — 環境構築・基盤整備
- モノレポ構成でリポジトリ作成（`frontend/` / `backend/` / `supabase/`）
- Next.js・FastAPI プロジェクト初期化、`.env.example` 整備
- Supabase ローカル環境構築、Cloudflare R2 バケット作成、Gemini API キー取得

### Phase 1 — データベース構築
- `analysis_sessions` / `damage_logs` テーブル DDL・インデックス作成
- RLS ポリシー設定（`auth.uid() = user_id`）
- マイグレーション `20250401000000`〜`20250401000002` 作成済み
  - `20250401000002`: `user_id` FK を `ON DELETE CASCADE` に変更

### Phase 2 — バックエンド実装
- `app/core/config.py`：環境変数管理（pydantic-settings）
- `app/core/security.py`：JWT検証（audience="authenticated"）・slowapi レートリミット
- `app/db/supabase.py`：Supabase クライアント初期化
- `app/services/r2.py`：Cloudflare R2 ストリーミング連携
- `app/services/video.py`：FFmpeg ストリーミング処理・JPEG フレーム切り出し
- `app/services/ocr/gemini.py`：Gemini Vision API OCR（リトライ・指数バックオフ）
- `app/services/aggregator.py`：ダメージ集計・重複排除
- 全 API エンドポイント実装（upload / analysis / results / history）
- バックグラウンド処理フロー（R2 → FFmpeg → OCR → SSE → DB）
- `app/schemas/health.py` に `HealthResponse` を分離
- `results` / `analysis` エンドポイントにセッション所有者チェック追加

### Phase 3 — フロントエンド実装
- `lib/supabase.ts` / `lib/auth.ts` / `lib/api.ts` / `lib/sse.ts`
- `types/index.ts` 共通型定義
- `proxy.ts`（Next.js 16 規約）による `/history` 認証保護・クッキー同期修正
- `components/common/`：Header・AuthGuard・LoadingSpinner・ProgressBar（ARIA属性付き）
- `components/upload/`：UploadDropzone・VideoUrlInput
- `components/analysis/`：DamageLogViewer（仮想スクロール）・SummaryCard・ExportButton
- `contexts/AuthContext.tsx`：認証状態グローバル管理
- `hooks/useAnalysisStream.ts`：SSE カスタムフック
- ページ実装：`/`・`/analysis/[sessionId]`・`/auth/login`・`/auth/signup`・`/history`
- OpenCode・CodeRabbit 両レビューの指摘事項をすべて修正済み

---

## 🔧 作業中・未完了のタスク

### Phase 4 — デプロイ・本番設定
- [ ] Vercel プロジェクト作成・環境変数設定・デプロイ
- [ ] Render サービス作成・Dockerfile 作成（FFmpeg インストール含む）・デプロイ
- [ ] Supabase 本番プロジェクト作成・`supabase db push` で本番適用

### Phase 5 — テスト・品質保証
- [ ] バックエンドユニットテスト（OCR・集計・R2 操作）
- [ ] フロントエンド E2E フロー手動確認
- [ ] 50分動画でのパフォーマンス確認

---

## 👉 次のアクション（再開時の起点）

**Phase 4 デプロイ作業に着手する。**

1. `develop` ブランチから `feature/phase4-deploy` ブランチを作成
2. バックエンド用 `Dockerfile` を作成（Python 3.12-slim + FFmpeg インストール）
3. Render / Vercel / Supabase 本番の環境変数・設定確認を進める

---

## ⚠️ 懸念事項・確認が必要な点

- **Supabase 本番マイグレーション**: `20250401000002_alter_user_id_fk_cascade.sql` は本番 DB にまだ未適用。`supabase db push` を本番環境で実施する前に確認が必要
- **YouTube ダウンロード（yt-dlp）**: バックエンドコードは実装済みだが、Render の無料プランでの実行時間制限（30分タイムアウト）が長時間動画で問題になる可能性がある
- **R2 のファイルサイズ上限**: `CLAUDE.md` に「File size limit: TBD」と記載があるまま。デプロイ前に上限値を決定し、フロントエンド・バックエンド双方に反映する必要がある
- **Gemini API の無料枠**: 本番運用開始後に消費量をモニタリングする仕組みを検討する
