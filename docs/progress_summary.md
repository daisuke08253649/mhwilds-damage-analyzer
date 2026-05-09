# 実装進捗サマリー

最終更新: 2026-05-09

---

## ✅ 完了済みのタスク

### Phase 1 — データベース構築（完了）
- `analysis_sessions` テーブル DDL 作成（RLS ポリシー含む）
- `damage_logs` テーブル DDL 作成（RLS ポリシー含む）
- インデックス作成（`session_id`, `user_id`）
- PR #1 → `develop` にマージ済み

### Phase 2 — バックエンド実装（完了）
- `app/core/config.py`：pydantic-settings による環境変数管理
- `app/core/security.py`：JWT 検証・`get_current_user` / `get_current_user_required` / slowapi レートリミット
- `app/core/sse.py`：SSEQueueManager（asyncio.Queue ベース）
- `app/db/supabase.py`：AsyncClient + asyncio.Lock による二重チェックロック初期化
- `app/services/r2.py`：Cloudflare R2 操作（upload / get / delete）
- `app/services/video.py`：FFmpeg ストリーミング処理・JPEG フレーム抽出・SOI/EOI マーカー分割
- `app/services/aggregator.py`：ダメージ集計（DoneEventData 返却）
- `app/services/ocr/gemini.py`：Gemini OCR（google-genai SDK、リトライ×3）
- `app/api/v1/upload.py`：ファイル・YouTube アップロードエンドポイント
- `app/api/v1/analysis.py`：SSE ストリームエンドポイント
- `app/api/v1/results.py`：サマリー・ログ・エクスポートエンドポイント
- `app/api/v1/history.py`：解析履歴エンドポイント（要認証）
- `app/main.py`：FastAPI アプリ本体（CORS・ミドルウェア・HealthResponse）
- `.coderabbit.yaml`：CodeRabbit 全ブランチレビュー設定
- PR #2（.coderabbit.yaml）→ `develop` マージ済み
- PR #3（Phase 2 全実装 + CodeRabbit 2ラウンド修正）→ `develop` マージ済み

---

## 🔧 作業中・未完了のタスク

### Phase 3 — フロントエンド実装（未着手）

以下すべて未実装：

**プロジェクト基盤**
- `lib/supabase.ts`
- `lib/auth.ts`
- `lib/api.ts`
- `lib/sse.ts`
- `types/index.ts`
- `middleware.ts`（`/history` を認証必須ルートとして保護）

**共通コンポーネント**
- `components/common/Header.tsx`
- `components/common/AuthGuard.tsx`
- `components/common/LoadingSpinner.tsx`
- `components/common/ProgressBar.tsx`

**アップロード画面（`app/page.tsx`）**
- `components/upload/UploadDropzone.tsx`（react-dropzone）
- `components/upload/VideoUrlInput.tsx`

**解析画面（`app/analysis/[sessionId]/page.tsx`）**
- `useAnalysisStream(sessionId)` カスタムフック
- `components/analysis/DamageLogViewer.tsx`（@tanstack/react-virtual）
- `components/analysis/SummaryCard.tsx`
- `components/analysis/ExportButton.tsx`

**認証画面**
- `app/auth/login/page.tsx`
- `app/auth/signup/page.tsx`

**履歴画面**
- `app/history/page.tsx`

### Phase 4 — デプロイ（未着手）
### Phase 5 — テスト・QA（未着手）

---

## 👉 次のアクション（再開時の起点）

1. **フィーチャーブランチ作成**
   ```bash
   git checkout develop
   git checkout -b feature/phase3-frontend
   ```

2. **必要パッケージのインストール**（`frontend/` ディレクトリで実行）
   ```bash
   npm install @supabase/supabase-js @supabase/ssr
   npm install @tanstack/react-query @tanstack/react-virtual
   npm install react-dropzone
   npm install --save-dev @types/react-dropzone
   ```

3. **Context7 でライブラリ最新 docs を確認してから実装開始**
   - `@supabase/ssr`（Next.js App Router 向け SSR クライアント初期化）
   - `@tanstack/react-query`（QueryClientProvider の配置）
   - `@tanstack/react-virtual`（useVirtualizer の API）
   - `react-dropzone`（useDropzone の API）

4. **実装順序**（依存関係の少ないものから）
   1. `types/index.ts`
   2. `lib/supabase.ts` + `lib/auth.ts`
   3. `lib/api.ts` + `lib/sse.ts`
   4. `middleware.ts`
   5. 共通コンポーネント（Header, LoadingSpinner, ProgressBar, AuthGuard）
   6. `app/layout.tsx` 更新（QueryClientProvider, Header）
   7. アップロード画面（`page.tsx`, UploadDropzone, VideoUrlInput）
   8. 解析画面（useAnalysisStream, DamageLogViewer, SummaryCard, ExportButton）
   9. 認証画面（login, signup）
   10. 履歴画面（history）

---

## ⚠️ 懸念事項・確認が必要な点

1. **`frontend-design/SKILL.md` が存在しない**
   CLAUDE.md では「フロントエンドコードを書く前に `frontend-design/SKILL.md` を読むこと」と指示されているが、リポジトリに該当ファイルが見当たらない。再開時にユーザーに確認するか、存在する場合はパスを教えてもらう。

2. **Next.js 16.2.4 の破壊的変更**
   `frontend/AGENTS.md` に「トレーニングデータと異なる破壊的変更がある」と警告あり。`node_modules/next/dist/docs/` を参照必須。特に `params` が `Promise<{...}>` になっている点（Next.js 15 以降）は確認済み。

3. **環境変数の設定状況**
   フロントエンドが必要とする環境変数（`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_BASE_URL`）が `.env.local` に設定済みか確認が必要。

4. **Supabase ローカル環境の稼働状況**
   フロントエンドを動作確認するには `supabase start`（Docker 必要）とバックエンドの起動が前提。ローカルで動作確認できる環境か確認が必要。
