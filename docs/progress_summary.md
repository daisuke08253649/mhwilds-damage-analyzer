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

### Phase 4 — デプロイ・本番設定（完了）
- Supabase 本番プロジェクト作成・`supabase db push` で本番 DB にマイグレーション適用済み
- Render（バックエンド）デプロイ済み・ヘルスチェック（`/health`）通過確認済み
  - URL: https://mhwilds-damage-analyzer.onrender.com
  - `Dockerfile` / `.dockerignore` 作成済み（FFmpeg・libmagic インストール済み）
- Vercel（フロントエンド）デプロイ済み・画面表示確認済み
  - URL: https://mhwilds-damage-analyzer.vercel.app
- CORS 設定を Vercel 本番 URL（`https://mhwilds-damage-analyzer.vercel.app`）に限定済み

### Phase 5 — テスト・バグ修正（大部分完了）
- ユニットテスト 26 件全パス確認済み
  - `tests/test_aggregator.py`（8件）
  - `tests/test_ocr_openrouter.py`（8件）← Gemini 用テストに書き換え済み
  - `tests/test_r2.py`（6件）
  - `tests/test_analysis_sse.py`（4件）
- SSE 二重シリアライズバグ修正済み
- 履歴ページ表示不具合修正済み
- OCR バックエンドを **Gemini（google-genai SDK）** に変更済み
- 設定管理を `pydantic-settings` → **`python-dotenv`** に簡略化済み

---

## 🔧 作業中・未完了のタスク

### Phase 5 — テスト・品質保証（残タスク）
- [ ] 実際の動画ファイルを使ったE2Eフロー手動確認（アップロード → 解析 → 結果表示）
- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

**本番環境での E2E 動作確認。**

1. https://mhwilds-damage-analyzer.vercel.app にアクセス
2. 実際の動画ファイル（短め）をアップロードして解析が完了するか確認
3. ログイン → 履歴ページ（`/history`）が正しく表示されるか確認
4. 問題があれば本番ログ（Render ダッシュボード）を確認して修正

---

## ⚠️ 懸念事項・確認が必要な点

- **Render 無料プランのスリープ**: 無料プランは 15 分間リクエストがないとスリープする。初回リクエスト時に起動まで数十秒かかる場合がある
- **Gemini API 無料枠**: `gemma-4-26b-a4b-it` の無料枠に制限がある。長時間動画では処理に時間がかかる可能性あり。`GEMINI_MODEL` 環境変数で別モデルに切り替え可能
- **Supabase 本番 RLS**: ダッシュボードで RLS が有効になっているか目視確認を推奨
- **R2 ファイルサイズ上限**: `CLAUDE.md` に「TBD」のまま。必要に応じて `MAX_UPLOAD_SIZE_MB` 環境変数で設定可能
- **YouTube ダウンロード（yt-dlp）**: Render 無料プランの 30 分タイムアウトが長時間動画で問題になる可能性がある
