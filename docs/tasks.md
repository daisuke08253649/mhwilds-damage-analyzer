[[design]]
# タスク一覧
## MHWilds ダメージ解析 Webアプリケーション

---

## Phase 1 — 環境構築・基盤整備

### インフラ・サービス初期設定
- [ ] Supabase CLI インストール・`supabase init` でローカル開発環境構築
- [ ] Cloudflare R2 バケット作成・アクセスキー発行（パブリックアクセス無効化）
- [ ] Gemini API キー取得

### リポジトリ・プロジェクト初期化
- [ ] モノレポ構成でリポジトリ作成（`frontend/` / `backend/` / `supabase/`）
- [ ] Next.js プロジェクト初期化（`frontend/`）
- [ ] FastAPI プロジェクト初期化（`backend/`）、`requirements.txt` 整備
- [ ] `.env.local` テンプレート作成（`.env.example` として Git 管理）
- [ ] `.gitignore` 設定（`.env.local` / `__pycache__` 等を除外）

---

## Phase 2 — データベース構築

### マイグレーション作成（`supabase/migrations/`）
- [ ] `analysis_sessions` テーブルの DDL 作成
  - カラム：`id`, `user_id`, `video_name`, `video_source`, `status`, `total_damage`, `max_damage`, `avg_damage`, `hit_count`, `created_at`, `completed_at`
- [ ] `damage_logs` テーブルの DDL 作成
  - カラム：`id`, `session_id`, `timestamp_ms`, `damage_value`, `frame_index`
- [ ] インデックス作成（`damage_logs.session_id`、`analysis_sessions.user_id` 等）
- [ ] RLS ポリシー設定
  - `analysis_sessions`：`auth.uid() = user_id` のみ参照可
  - `damage_logs`：紐づくセッションのみ参照可
- [ ] `supabase db reset` でローカル適用確認
- [ ] `supabase db push` で本番適用

---

## Phase 3 — バックエンド実装

### プロジェクト基盤
- [ ] `app/core/config.py`：環境変数の読み込み設定（`pydantic-settings` 使用）
- [ ] `app/core/security.py`：`slowapi` によるレートリミット設定
  - アップロード：10回 / 時 / IP
  - OCR解析：5回 / 時 / IP
- [ ] CORS 設定（`ALLOWED_ORIGINS` 環境変数から動的設定）
- [ ] `app/db/supabase.py`：`supabase-py` クライアント初期化（Service Role Key 使用）

### Cloudflare R2 連携
- [ ] `app/services/r2.py` 実装（`boto3` S3 互換 API 使用）
  - `upload_fileobj()`：ストリーミングアップロード
  - `get_object()`：ストリーム取得
  - `delete_object()`：削除

### 動画処理
- [ ] `app/services/video.py`：FFmpeg ストリーミング処理実装
  - R2 ストリームを FFmpeg の stdin に流し込み（別スレッド、1MB ずつ書き込み）
  - stdout から SOI（`FF D8`）〜 EOI（`FF D9`）マーカーで JPEG を1枚ずつ切り出し
  - 切り出した JPEG バイト列を `PIL.Image` に変換（メモリ上のみ、ディスク書き込みなし）
- [ ] YouTube 動画取得（`yt-dlp` で R2 にストリーミング保存、720p 以下優先）

### OCR 処理
- [ ] `app/services/ocr/base.py`：`OCRServiceBase` 抽象クラス定義（`recognize(frame: Image) -> OCRResult`）
- [ ] `app/services/ocr/gemini.py`：`GeminiOCRService` 実装
  - フレーム画像を Gemini Vision API に送信
  - プロンプト設計（「ダメージ数値を JSON 形式で返す」）
  - レスポンスパース（`{"damages": [数値, ...]}` 形式）
  - リトライ実装（最大3回、指数バックオフ）
- [ ] `app/services/ocr/custom_model.py`：将来用スタブクラス作成
- [ ] `OCR_BACKEND` 環境変数による OCR クラスの切り替え機構実装

### 集計処理
- [ ] `app/services/aggregator.py`：ダメージ集計ロジック実装
  - 連続する同一数値・タイムスタンプの重複排除
  - 総ダメージ・最大ダメージ・平均ダメージ・ヒット数の集計

### API エンドポイント
- [ ] `app/schemas/analysis.py`：Pydantic スキーマ定義（リクエスト・レスポンス）
- [ ] `POST /api/v1/upload/file`
  - MIMEタイプ検証（`python-magic`）・拡張子チェック・ファイルサイズチェック
  - DB にセッションレコード作成（`status: pending`）
  - R2 にストリーミングアップロード
  - `BackgroundTasks` でバックグラウンド処理起動
  - `session_id` を 202 レスポンスで返却
- [ ] `POST /api/v1/upload/youtube`
  - YouTube URL バリデーション
  - DB にセッションレコード作成
  - `BackgroundTasks` で yt-dlp ダウンロード → 処理起動
- [ ] `GET /api/v1/analysis/{session_id}/stream`（SSE）
  - `asyncio.Queue` を監視し `damage` / `done` / `error` イベントを逐次配信
- [ ] `GET /api/v1/results/{session_id}/summary`：サマリー取得
- [ ] `GET /api/v1/results/{session_id}/logs`：ダメージログ一覧取得（ページネーション対応）
- [ ] `GET /api/v1/results/{session_id}/export`：CSV / JSON エクスポート
- [ ] `GET /api/v1/history`：解析履歴一覧取得（要認証、ページネーション対応）

### 認証連携（FastAPI）
- [ ] `Authorization: Bearer` ヘッダーから JWT を取得する依存関数実装
- [ ] `SUPABASE_JWT_SECRET` で署名検証し `user_id` を取得する処理実装（未ログイン時は `None` を許容）

### バックグラウンド処理フロー
- [ ] セッション `status` を `processing` に更新
- [ ] R2 から動画ストリーム取得 → FFmpeg → JPEG 切り出し → OCR のループ実装
- [ ] フレームごとに `damage_logs` INSERT + SSE キューへプッシュ
- [ ] 全フレーム完了後にサマリー集計・`analysis_sessions` UPDATE（`status: done`）
- [ ] `finally` ブロックで R2 動画ファイルを確実に削除

---

## Phase 4 — フロントエンド実装

### プロジェクト基盤
- [ ] `lib/supabase.ts`：Supabase クライアント初期化（`@supabase/supabase-js` / `@supabase/ssr`）
- [ ] `lib/auth.ts`：Supabase Auth ヘルパー関数
- [ ] `lib/api.ts`：FastAPI クライアント関数（`session_id` ベースの API 呼び出し）
- [ ] `lib/sse.ts`：SSE 受信ユーティリティ（`EventSource` ラッパー）
- [ ] `types/index.ts`：共通型定義（`AnalysisSession`, `DamageLog`, `Summary` 等）
- [ ] Next.js Middleware 設定（`/history` を認証必須ルートとして保護）

### 共通コンポーネント
- [ ] `components/common/Header.tsx`：ナビゲーション（認証状態に応じてメニュー切り替え）
- [ ] `components/common/AuthGuard.tsx`：認証チェックラッパー
- [ ] `components/common/LoadingSpinner.tsx`：共通ローディング表示
- [ ] `components/common/ProgressBar.tsx`：共通進捗バー

### 動画アップロード画面（`app/page.tsx`）
- [ ] `components/upload/UploadDropzone.tsx`
  - `react-dropzone` を使用したドラッグ＆ドロップ
  - バリデーション（拡張子 mp4 / mov / avi、ファイルサイズ上限）
  - アップロード後、`/analysis/{session_id}` にリダイレクト
- [ ] `components/upload/VideoUrlInput.tsx`：YouTube URL 入力フォーム

### 解析中・結果画面（`app/analysis/[sessionId]/page.tsx`）
- [ ] `useAnalysisStream(sessionId)` カスタムフック実装
  - `EventSource` で SSE 接続
  - `damage` / `done` / `error` イベントを購読
  - ログ配列・進捗・サマリー・ステータスを state 管理
- [ ] `components/analysis/DamageLogViewer.tsx`
  - `@tanstack/react-virtual` による仮想スクロール
  - 各行：`MM:SS.mmm　｜　+{damage}` 形式で時系列昇順表示
- [ ] `components/analysis/SummaryCard.tsx`
  - 総ダメージを大フォントで強調表示
  - 平均・最大・ヒット数をカード形式で並列表示
- [ ] `components/analysis/ExportButton.tsx`：CSV / JSON エクスポートボタン

### 認証画面
- [ ] `app/auth/login/page.tsx`：メール＋パスワードログインフォーム
- [ ] `app/auth/signup/page.tsx`：サインアップフォーム

### 解析履歴画面（`app/history/page.tsx`）
- [ ] 過去セッション一覧表示（日時・動画名・総ダメージ）
- [ ] 各セッションクリックで `/analysis/{session_id}` に遷移

### 状態管理
- [ ] React Context：認証状態のグローバル管理
- [ ] `@tanstack/react-query`：サーバー状態のキャッシュ・再取得管理

---

## Phase 5 — デプロイ・本番設定

### Vercel（フロントエンド）
- [ ] 環境変数設定（`NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_API_BASE_URL`）
- [ ] デプロイ・動作確認

### Render（バックエンド）
- [ ] `Dockerfile` 作成（FFmpeg インストール含む）
- [ ] 環境変数設定（Supabase / R2 / Gemini / OCR 関連）
- [ ] デプロイ・動作確認
- [ ] CORS 設定を Vercel の本番 URL に限定

### Supabase 本番
- [ ] `supabase db push` で本番 DB にマイグレーション適用
- [ ] RLS ポリシー有効化・動作確認

---

## Phase 6 — テスト・品質保証

- [ ] バックエンド：`tests/` にユニットテスト追加
  - OCR サービス（モック Gemini レスポンス）
  - 集計ロジック（重複排除・統計値）
  - R2 操作（モック `boto3`）
- [ ] フロントエンド：アップロード → 解析 → 結果表示の E2E フロー手動確認
- [ ] 50分動画での処理時間・メモリ使用量の確認
- [ ] Gemini API 無料枠の消費量モニタリング設定

---

## 今後の対応（Phase 4 以降）

- [ ] OAuth 対応（Google / GitHub）
- [ ] ファインチューニング用訓練データ収集・アノテーション方針決定
- [ ] カスタム OCR モデル（`custom_model.py`）実装・`OCR_BACKEND=finetuned` 切り替え確認
- [ ] Celery + Redis によるバックグラウンド処理のスケールアップ対応
- [ ] 利用規約・プライバシーポリシーの策定・ページ追加
