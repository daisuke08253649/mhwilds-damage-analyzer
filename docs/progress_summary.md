# 実装進捗サマリー

最終更新: 2026-06-09

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

### Phase 2 — バックエンド実装
- 全モジュール実装済み（config / security / supabase / r2 / video / ocr / aggregator）
- 全 API エンドポイント実装済み（upload / analysis / results / history）
- バックグラウンド処理フロー完成
- `video.py` バグ修正済み（FFmpeg stderr PIPE 化、yt-dlp mkdtemp 対応）

### Phase 3 — フロントエンド実装
- 全ページ・コンポーネント実装済み（`/` / `/analysis/[sessionId]` / `/auth/*` / `/history`）
- SSE カスタムフック・ライブラリ実装済み
- OpenCode・CodeRabbit 両レビューの指摘事項をすべて修正済み

### Phase 5 — テスト（一部完了）
- `backend/pytest.ini`・`backend/requirements-dev.txt` 作成済み
- ユニットテスト追加・全パス確認済み（26テスト）
  - `tests/test_aggregator.py`（8件）
  - `tests/test_ocr_gemini.py`（7件）
  - `tests/test_r2.py`（6件）
  - `tests/test_analysis_sse.py`（4件）← 今回追加

---

## 🔧 作業中・未完了のタスク

### 未コミットの変更（`feature/phase5-tests` ブランチ）

- `backend/app/api/v1/analysis.py`（modified）
  - **SSE 二重シリアライズバグ修正**: `ServerSentEvent(data=json.dumps(...))` → `ServerSentEvent(data={...})` に変更
    - FastAPI 0.136.1 の `ServerSentEvent.data` は自動 JSON シリアライズするため、`json.dumps` を事前に渡すと二重シリアライズが発生し、フロントエンドで `JSON.parse` がオブジェクトではなく文字列を返していた
  - **SSE 所有者チェック削除**: `EventSource` がカスタムヘッダーを送れない仕様により、ログイン済みユーザーが自分のセッションにアクセスできなかった問題を修正
    - `user_id` 引数・`get_current_user` 依存を削除
    - セキュリティ: セッション UUID（122 bit）の推測困難性で代替
  - `_or_zero` ヘルパー関数追加・`DoneEventData.model_dump()` 採用
  - `CancelledError` 処理をコメントに変更
- `backend/tests/test_analysis_sse.py`（untracked）← 新規追加

### Phase 5 — 不具合修正（完了）

- **[x] 履歴ページ（`/history`）が表示されない** → 修正済み
  - `backend/app/schemas/analysis.py`: `HistorySessionItem` に `status: str` 追加
  - `backend/app/api/v1/history.py`: SELECT に `status` 追加
  - `frontend/src/types/index.ts`: `HistoryItem` 型を追加
  - `frontend/src/lib/api.ts`: `getHistory` が `data.sessions` を返すよう修正、型を `HistoryItem[]` に変更
  - `frontend/src/app/history/page.tsx`: 型を `HistoryItem` に変更

### Phase 4 — デプロイ・本番設定（未着手）
- [ ] Vercel プロジェクト作成・環境変数設定・デプロイ
- [ ] Render サービス作成・Dockerfile 作成（FFmpeg インストール含む）・デプロイ
- [ ] Supabase 本番プロジェクト作成・`supabase db push` で本番適用

### Phase 5 — テスト・品質保証（残タスク）
- [ ] 50分動画でのパフォーマンス確認
- [ ] Gemini API 無料枠の消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

**履歴ページ修正・SSE バグ修正・テスト追加をまとめてコミット・PR 作成。**

1. 未コミットの変更（`analysis.py` + `test_analysis_sse.py` + 今回の履歴修正）をコミット
2. PR 作成（`feature/phase5-tests` → `main`）
3. Phase 4 デプロイへ進む

---

## ⚠️ 懸念事項・確認が必要な点

- **未コミット変更あり**: `feature/phase5-tests` ブランチに `analysis.py` の修正と `test_analysis_sse.py` が未コミット。履歴ページ修正と合わせて一括コミットする
- **`results.py` の同様のバグ**: `get_summary` / `get_logs` / `export_results` も `or 0` パターンを使っているが、これらは `fetch` 経由で Authorization ヘッダーを送れるため動作上の問題はない。ただし `_or_zero` ヘルパーへの統一は今後の改善候補
- **Supabase 本番マイグレーション**: `20250401000002_alter_user_id_fk_cascade.sql` は本番 DB に未適用。Phase 4 デプロイ時に要確認
- **YouTube ダウンロード（yt-dlp）**: Render 無料プランの 30 分タイムアウトが長時間動画で問題になる可能性がある
- **R2 ファイルサイズ上限**: `CLAUDE.md` に「TBD」のまま。デプロイ前に上限値を決定する必要がある
