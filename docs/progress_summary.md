# 実装進捗サマリー

最終更新: 2026-05-28

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

### Phase 5 — テスト（一部完了）
- `backend/pytest.ini`・`backend/requirements-dev.txt` 作成
- ユニットテスト追加：`tests/test_aggregator.py`・`tests/test_ocr_gemini.py`・`tests/test_r2.py`
- E2E テスト中に発見したバックエンドバグを修正（下記「作業中」参照）

---

## 🔧 作業中・未完了のタスク

### Phase 4 — デプロイ・本番設定（未着手）
- [ ] Vercel プロジェクト作成・環境変数設定・デプロイ
- [ ] Render サービス作成・Dockerfile 作成（FFmpeg インストール含む）・デプロイ
- [ ] Supabase 本番プロジェクト作成・`supabase db push` で本番適用

### Phase 5 — テスト・品質保証（進行中）
- [x] バックエンドユニットテスト（OCR・集計・R2 操作）← 追加済み、パス確認が必要
- [ ] **フロントエンド E2E フロー：SSE リアルタイム表示が動作していない**（要調査・修正）
- [ ] 50分動画でのパフォーマンス確認
- [ ] Gemini API 無料枠の消費量モニタリング設定

### バックエンド修正済みバグ（未コミット、`feature/phase5-tests` ブランチ）
- `backend/app/services/video.py`
  - FFmpeg の `stderr` を `DEVNULL` から `PIPE` に変更し、エラー原因を可視化
  - stderr を専用スレッドで読み取ることでパイプバッファのデッドロックを防止
  - エラーメッセージに FFmpeg の stderr 出力（末尾500文字）を含めるよう改善
  - `download_youtube_to_r2`：`NamedTemporaryFile` → `mkdtemp()` に変更
    - Windows で事前作成された空ファイルへの yt-dlp rename 失敗により 0 バイトが R2 にアップロードされていた問題を修正
    - アップロード前にファイル存在・サイズをバリデーション追加
    - `shutil.rmtree` でディレクトリごとクリーンアップ（yt-dlp の `.part` ファイルも含む）

---

## 👉 次のアクション（再開時の起点）

**フロントエンドの SSE リアルタイム表示が動作しない問題の調査・修正から再開する。**

1. ブラウザの DevTools → Network タブで `/api/v1/analysis/{sessionId}/stream` の SSE 接続を確認
   - イベントが届いているか・エラーが出ているかを確認
2. `hooks/useAnalysisStream.ts` の `EventSource` 接続ロジック・イベントハンドラを確認
3. `app/analysis/[sessionId]/page.tsx` でフックの戻り値が UI に反映されているか確認
4. 問題修正後、バックエンド修正（`video.py` 等）と合わせてコミット・PR を作成

---

## ⚠️ 懸念事項・確認が必要な点

- **SSE リアルタイム表示不動作**: YouTube URL 投稿後のダメージ表示・進捗バーが更新されない。バックエンドのバグ修正（yt-dlp 0バイト問題）により正常にデータが流れるようになったので、フロントエンド側の問題である可能性が高い
- **バックエンドの未コミット変更**: `feature/phase5-tests` ブランチに `video.py` 等の修正が未コミット。再開時に確認して一緒にコミットする
- **Supabase 本番マイグレーション**: `20250401000002_alter_user_id_fk_cascade.sql` は本番 DB にまだ未適用。Phase 4 デプロイ時に要確認
- **YouTube ダウンロード（yt-dlp）**: Render 無料プランでの実行時間制限（30分タイムアウト）が長時間動画で問題になる可能性がある
- **R2 のファイルサイズ上限**: `CLAUDE.md` に「File size limit: TBD」と記載のまま。デプロイ前に上限値を決定し実装に反映する必要がある
