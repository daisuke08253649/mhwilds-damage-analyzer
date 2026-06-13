# 実装進捗サマリー

最終更新: 2026-06-13

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
- `video.py` バグ修正済み（FFmpeg stderr PIPE 化、yt-dlp mkdtemp 対応・タイムアウト設定）

### Phase 3 — フロントエンド実装
- 全ページ・コンポーネント実装済み（`/` / `/analysis/[sessionId]` / `/auth/*` / `/history`）
- SSE カスタムフック・ライブラリ実装済み
- OpenCode・CodeRabbit 両レビューの指摘事項をすべて修正済み

### Phase 5 — テスト・バグ修正（完了、`develop` 反映済み）
- `backend/pytest.ini`・`backend/requirements-dev.txt` 作成済み
- ユニットテスト 26 件（全パス確認済み）
  - `tests/test_aggregator.py`（8件）
  - `tests/test_ocr_openrouter.py`（8件）← Gemini 用テストに書き換え済み
  - `tests/test_r2.py`（6件）
  - `tests/test_analysis_sse.py`（4件）
- SSE 二重シリアライズバグ修正（`analysis.py`）
- 履歴ページ（`/history`）表示不具合修正
- OCR バックエンドを **Gemini（google-genai SDK）** に変更・`develop` マージ済み
  - `model.py` に `GeminiOCRService` 実装
  - 設定管理を `pydantic-settings` → **`python-dotenv`** に簡略化
  - モデル名を `GEMINI_MODEL` 環境変数で切り替え可能に
  - `GEMINI_API_KEY` / `GEMINI_MODEL` を `.env.example` に追加

---

## 🔧 未完了のタスク

### Phase 4 — デプロイ・本番設定（未着手）
- [ ] Render サービス作成・`Dockerfile` 作成（FFmpeg・Python インストール）・デプロイ
- [ ] Render 環境変数設定（Supabase / R2 / Gemini / OCR 関連）
- [ ] CORS 設定を Vercel の本番 URL に限定
- [ ] Vercel プロジェクト作成・環境変数設定・デプロイ
- [ ] Supabase 本番プロジェクト作成・`supabase db push` で本番マイグレーション適用
- [ ] RLS ポリシー有効化・動作確認

### Phase 5 — テスト・品質保証（残タスク）
- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

**Phase 4 デプロイへ。**

1. Render の `Dockerfile` 作成（FFmpeg・Python インストール）
2. Render 環境変数設定・デプロイ・動作確認
3. Vercel 環境変数設定・デプロイ・動作確認
4. Supabase 本番マイグレーション適用（`supabase db push`）

---

## ⚠️ 懸念事項・確認が必要な点

- **Supabase 本番マイグレーション**: `20250401000002_alter_user_id_fk_cascade.sql` は本番 DB に未適用。Phase 4 デプロイ時に要確認
- **R2 ファイルサイズ上限**: `CLAUDE.md` に「TBD」のまま。デプロイ前に上限値を決定する必要がある
- **YouTube ダウンロード（yt-dlp）**: Render 無料プランの 30 分タイムアウトが長時間動画で問題になる可能性がある
- **Gemini API 無料枠**: `gemma-4-26b-a4b-it` は無料枠に制限がある。長時間動画では処理に時間がかかる可能性あり。本番運用では `GEMINI_MODEL` 環境変数でモデルを切り替えること
