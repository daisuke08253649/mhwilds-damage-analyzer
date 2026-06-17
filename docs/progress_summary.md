# 実装進捗サマリー

最終更新: 2026-06-17

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
- 本番環境 E2E 確認中に発生したバグを順次修正済み（下記）

#### 本番環境で修正したバグ（2026-06-17）

| # | 症状 | 原因 | 修正内容 |
|---|---|---|---|
| 1 | CORS エラー | `ALLOWED_ORIGINS` 末尾に `/` がついていた | Render 環境変数から末尾スラッシュを削除 |
| 2 | 500エラー（Supabase） | `SUPABASE_URL` に `/rest/v1` が含まれ二重パスになっていた | Render 環境変数をホスト名のみに修正 |
| 3 | yt-dlp に Node.js が必要 | Dockerfile に Node.js が未インストール | `nodejs` パッケージを Dockerfile に追加 |
| 4 | yt-dlp が Node.js を認識しない | Debian では `nodejs` バイナリ名が `node` でない | Dockerfile に `node` → `nodejs` シンボリックリンク追加、`--js-runtimes node:/usr/bin/nodejs` 指定 |
| 5 | stderr ログが途中で切れる | `stderr_text[:300]` で切り捨てていた | 上限を 2000 文字に拡張 |

---

## 🔧 作業中・未完了のタスク

### YouTube URL 機能が動作しない（未解決）

- **症状**: yt-dlp が returncode=1 で失敗する
- **根本原因**: Render のサーバー IP を YouTube がボットとみなしブロック
  ```
  ERROR: [youtube] Sign in to confirm you're not a bot.
  Use --cookies-from-browser or --cookies for the authentication.
  ```
- **結論**: Render 無料プランではクラウド IP がブロックされるため、コード修正では解決不可
- **未決定**: YouTube URL 機能を無効化するか、別の対処をするか

### E2E フロー確認（ファイルアップロード）

- YouTube URL は上記の理由で未確認
- **ファイルアップロード経由の E2E フローはまだ未確認**（動作する可能性は高い）

### その他 Phase 5 残タスク

- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

1. **YouTube URL 機能の方針を決定する**
   - 選択肢 A: 無効化（フロントエンドから YouTube URL 入力欄を非表示にする）← 推奨
   - 選択肢 B: Cookie 認証を設定する（Cookieが期限切れになるため本番運用には不向き）
   - 選択肢 C: 住宅用プロキシ経由にする（有料）

2. **ファイルアップロードの E2E フローを確認する**
   - https://mhwilds-damage-analyzer.vercel.app で短い動画ファイル（MP4）をアップロード
   - 解析が完了し、ダメージログ・サマリーが表示されるか確認

3. **方針が決まり次第、YouTube 機能の無効化 or 対応実装へ**

---

## ⚠️ 懸念事項・確認が必要な点

- **YouTube 機能**: Render（クラウド IP）から YouTube へのアクセスは YouTube のボット対策でブロックされる。根本的な解決には住宅用プロキシ（有料）か Cookie 認証が必要。現実的にはフロントエンドで機能を非表示にすることを推奨
- **Render の 404（`GET /`）**: デプロイ時に Render のヘルスチェックが `GET /` を叩くため 404 が出る。機能上の問題はないが、Render の **Health Check Path** を `/health` に設定すると解消できる
- **Render 無料プランのスリープ**: 15 分間リクエストがないとスリープする。初回リクエスト時に起動まで数十秒かかる
- **Gemini API 無料枠**: 長時間動画では消費量が大きくなる可能性がある。`GEMINI_MODEL` 環境変数で別モデルに切り替え可能
- **Supabase 本番 RLS**: ダッシュボードで RLS が有効になっているか目視確認を推奨
