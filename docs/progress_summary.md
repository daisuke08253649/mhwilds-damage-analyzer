# 実装進捗サマリー

最終更新: 2026-07-04

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

### Supabase 非アクティブ停止対策（2026-06-27）
- `/health` エンドポイントに Supabase DB ping を追加
  - 呼び出し時に `analysis_sessions` へ SELECT を実行し DB アクティビティを発生させる
  - DB エラー時も `status: "ok"` を返し、`db` フィールドで状態を表現
  - 変更ファイル：`backend/app/main.py` / `backend/app/schemas/health.py`
- `feature/keep-alive-health` ブランチで実装 → develop・main にマージ済み
- **→ 上記だけでは停止問題が解決せず、以下の追加対策を実施（2026-07-04）**

### Supabase 非アクティブ停止対策・第2弾（2026-07-04）

前回の `/health` 経由の対策（`GAS → Render(/health) → Supabase`）は、Render 無料プランのスリープ・コールドスタートに阻まれ、GAS の `UrlFetchApp` がタイムアウトして Supabase まで到達しない可能性があると判明。そこで **Render を経由せず GAS から Supabase に直接書き込む**方式に変更した。

- 新規テーブル `keep_alive_pings`（`id`, `pinged_at timestamptz default now()`）を追加
  - マイグレーション：`supabase/migrations/20260704000000_create_keep_alive_pings.sql`
  - RLS：`anon` ロールに対して INSERT のみ許可するポリシーを設定（SELECT/UPDATE/DELETE は不可）
- GAS 側の実行関数を `pingHealth`（Render `/health` 呼び出し）から `pingSupabaseKeepAlive`（Supabase REST API に直接 POST）に差し替え

```javascript
function pingSupabaseKeepAlive() {
  const props = PropertiesService.getScriptProperties();
  const url = props.getProperty('SUPABASE_URL') + '/rest/v1/keep_alive_pings';
  const anonKey = props.getProperty('SUPABASE_ANON_KEY');

  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    headers: {
      'apikey': anonKey,
      'Authorization': 'Bearer ' + anonKey,
      'Content-Type': 'application/json',
      'Prefer': 'return=minimal'
    },
    payload: JSON.stringify({}),
    muteHttpExceptions: true
  });

  Logger.log('status: %s / body: %s', response.getResponseCode(), response.getContentText());
}
```

- スクリプトプロパティに `SUPABASE_URL`（例: `https://xxxx.supabase.co`）と `SUPABASE_ANON_KEY` を設定する
- 既存の日次トリガーはそのまま使い、実行関数だけ `pingSupabaseKeepAlive` に差し替える
- 旧 `HEALTH_API` プロパティ・`pingHealth` 関数は不要になるが削除は必須ではない
- バックエンドの `/health` エンドポイントは変更なし（一般的なヘルスチェックとして継続利用）

---

## 🔧 作業中・未完了のタスク

### GAS の設定（ユーザー側で実施が必要・要更新）

Supabase の非アクティブ停止を防ぐため、GAS で1日1回 `keep_alive_pings` テーブルに直接 INSERT するトリガーをユーザー自身が設定する必要がある（Render 経由の旧方式から変更）。

上記「Supabase 非アクティブ停止対策・第2弾」の `pingSupabaseKeepAlive` 関数を GAS に貼り付け、日次トリガーを設定する：

- スクリプトプロパティ `SUPABASE_URL` に本番 Supabase プロジェクト URL、`SUPABASE_ANON_KEY` に本番 anon key を設定
- `supabase db push` で本番に `keep_alive_pings` テーブルが反映されていることを確認してから実行すること
- 実行関数を `pingSupabaseKeepAlive` に指定してトリガー登録：時間主導型 → 日付ベースのタイマー → 任意の時刻
- 手動実行してログで `status: 201` を確認し、Supabase Studio（本番）で `keep_alive_pings` に行が増えていることを確認
- 既存の `pingHealth` 関数・`HEALTH_API` プロパティは残っていても害はないが、トリガーの実行関数は必ず `pingSupabaseKeepAlive` に切り替えること

### その他 Phase 5 残タスク

- [ ] ファイルアップロードの E2E フロー確認（本番環境で短い MP4 をアップロードして解析完了まで確認）
- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

1. **`supabase db push` で本番に `keep_alive_pings` テーブルを反映し、GAS の設定を完了させる**（ユーザー側の作業）
   - スクリプトプロパティに `SUPABASE_URL` / `SUPABASE_ANON_KEY` を設定し、実行関数を `pingSupabaseKeepAlive` にして日次トリガーを有効化
   - 手動実行でログ（`status: 201`）を確認し、Supabase Studio で `keep_alive_pings` に行が増えていることを確認

2. **ファイルアップロードの E2E フローを確認する**
   - https://mhwilds-damage-analyzer.vercel.app で短い MP4 をアップロード
   - 解析中にダメージログがリアルタイムで流れ、完了後にサマリーが表示されるか確認
   - Render のログ（Dashboard → Logs）も同時に確認し、エラーが出ていないか見る

3. **E2E が正常に動いた場合**
   - 50 分動画でのメモリ・処理時間を確認
   - Gemini API 消費量のモニタリング設定

4. **E2E でエラーが出た場合**
   - Render のログと SSE のエラーメッセージを確認してから対処

---

## ⚠️ 懸念事項・確認が必要な点

- **Supabase 停止ポリシー**: 「1週間程度の非アクティブで停止」というポリシーが変更されている可能性がある。実装前に公式ドキュメントで現在の条件を確認推奨
- **Render 無料プランのスリープ**: 15 分間リクエストがないとスリープする。GAS の1日1回 ping では解決しない。現時点では対策なし（許容する方針）
- **Gemini API 無料枠**: 長時間動画では消費量が大きくなる可能性がある。`GEMINI_MODEL` 環境変数で別モデルに切り替え可能
- **OCR タイムアウト（30 秒）の妥当性**: Gemini API のレスポンスが安定して 30 秒以内に返るか未確認。問題が続く場合はタイムアウト値を調整する
- **YouTube URL 機能**: フロントエンドから非表示にしたが、バックエンドの `POST /api/v1/upload/youtube` エンドポイントは残存。将来的に対応する場合は Cookie 認証（`YOUTUBE_COOKIES_B64`）の仕組みを実装済み
- **Supabase 本番 RLS**: ダッシュボードで RLS が有効になっているか目視確認を推奨
