# 実装進捗サマリー

最終更新: 2026-07-04

---

## ✅ 完了済みのタスク

`tasks.md` の Phase 0〜Phase 4 は全項目完了。Phase 5（テスト・品質保証）は本番バグ修正まで完了し、残りはE2E確認等の検証タスクのみ（下記「作業中・未完了のタスク」参照）。

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

### Supabase 非アクティブ停止対策・第1弾（2026-06-27・効果不十分だったため第2弾に移行）
- `/health` エンドポイントに Supabase DB ping（SELECT）を追加
  - 変更ファイル：`backend/app/main.py` / `backend/app/schemas/health.py`
  - `feature/keep-alive-health` ブランチで実装 → develop・main にマージ済み
- → GAS → Render(`/health`) → Supabase という経路が、Render 無料プランのスリープ・コールドスタートで途切れる可能性があり、停止問題は解決しなかった

### Supabase 非アクティブ停止対策・第2弾（2026-07-04・完了）

Render を経由せず、**GAS から Supabase の REST API (PostgREST) に直接 INSERT** する方式に変更。Renderの起動状態に一切依存しないため、より確実。

- 新規テーブル `keep_alive_pings`（`id`, `pinged_at timestamptz default now()`）を追加
  - マイグレーション：`supabase/migrations/20260704000000_create_keep_alive_pings.sql`
  - RLS：`anon` ロールに対して INSERT のみ許可するポリシーを設定（SELECT/UPDATE/DELETE は不可）
  - CodeRabbit のレビュー指摘を受け、`grant insert on public.keep_alive_pings to anon;` を追加（RLSポリシーだけではPostgREST経由のGRANT権限が不足し `42501` エラーになるため）
- PR #10 として作成 → CodeRabbitレビュー対応済み → `main` にマージ済み、`develop` にも取り込み済み
- `supabase link --project-ref ctuuxnpupxzxyxzomlrs` → `supabase db push` で本番DBへの適用を完了・確認済み（`supabase migration list` で local/remote 一致を確認）
- GAS 側の実行関数を `pingHealth`（Render `/health` 呼び出し）から `pingSupabaseKeepAlive`（Supabase REST API に直接 POST）に差し替えるコードをユーザーに提示済み

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

- 本番 Supabase URL: `https://ctuuxnpupxzxyxzomlrs.supabase.co`
- anon key は機密性を考慮しコマンド出力には表示せず、ユーザー自身が Supabase ダッシュボード（Settings → API）または Vercel の環境変数 `NEXT_PUBLIC_SUPABASE_ANON_KEY` から取得する方針とした
- バックエンドの `/health` エンドポイントは変更なし（一般的なヘルスチェックとして継続利用）

---

## 🔧 作業中・未完了のタスク

### GAS の設定（ユーザー側で実施が必要・コード面の準備は完了）

本番DBへのテーブル反映は完了済み。あとはユーザー側でGASの設定を行うのみ：

1. Supabaseダッシュボード → Settings → API から anon key を取得（または Vercel の `NEXT_PUBLIC_SUPABASE_ANON_KEY` を流用）
2. GAS のスクリプトプロパティに `SUPABASE_URL`（`https://ctuuxnpupxzxyxzomlrs.supabase.co`）と `SUPABASE_ANON_KEY` を設定
3. 上記 `pingSupabaseKeepAlive` 関数を貼り付け
4. 手動実行してログで `status: 201` を確認
5. トリガーの実行関数を `pingHealth` → `pingSupabaseKeepAlive` に差し替え（日次・時刻は既存のままでよい）
6. Supabase Table Editor で `keep_alive_pings` に行が増えていることを確認
7. 旧 `pingHealth` 関数・`HEALTH_API` プロパティは残っていても害はないが、トリガーの対象だけは必ず切り替えること

**この設定が完了・動作確認できるまでは、今回のSupabase停止対策は「未検証」の状態。次回再開時にまずこの確認結果を聞くこと。**

### その他 Phase 5 残タスク（未着手）

- [ ] ファイルアップロードの E2E フロー確認（本番環境で短い MP4 をアップロードして解析完了まで確認）
- [ ] 50 分動画でのパフォーマンス・メモリ使用量確認
- [ ] Gemini API 消費量モニタリング設定

---

## 👉 次のアクション（再開時の起点）

1. **GAS設定の動作確認結果をユーザーに確認する**（最優先）
   - 上記手順でGAS設定が完了しているか、`status: 201` が確認できたか、`keep_alive_pings` に行が増えているかを聞く
   - まだの場合は設定をサポートする。数日〜1週間様子を見て、Supabaseが実際に停止しなくなったかも合わせて確認するとよい

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

- **Supabase 停止ポリシー（調査済み）**: 無料プランは7日間「DBへの実際のクエリ活動」がないと停止する。ダッシュボード閲覧やキャッシュ済みAPIレスポンスはカウントされないが、SELECT/INSERTなど実クエリはカウントされる。今回の`keep_alive_pings`への日次INSERTはこの条件を満たす設計だが、実際に停止しなくなるかは数日〜1週間の運用で要観察
- **Supabaseのデフォルト権限の変更（新たに判明）**: Supabaseは2026年5月30日以降に作成された新規プロジェクトから「テーブル作成時にanon/authenticatedへ自動GRANTしない」設定がデフォルトになった。今回のプロジェクトは2025年作成のため影響は薄いが、**今後新しいテーブルを追加する際はRLSポリシーだけでなく明示的な`grant`文も必要になる可能性がある点に注意**（`keep_alive_pings`のCodeRabbit指摘で判明）
- **pg_cronは不採用**: プロジェクトが一度停止するとコンピュートごと止まり内部cronジョブも道連れで止まるため、「自分で自分を起こす」用途には使えないと判断済み（再検討不要）
- **Render 無料プランのスリープ**: 15 分間リクエストがないとスリープする。今回の対策はSupabase側の停止のみを防ぐものであり、**Render自体のスリープ問題は未解決のまま**（許容する方針）。ユーザーが実際にアプリを使う際は初回アクセスでコールドスタート待ちが発生し得る
- **Gemini API 無料枠**: 長時間動画では消費量が大きくなる可能性がある。`GEMINI_MODEL` 環境変数で別モデルに切り替え可能
- **OCR タイムアウト（30 秒）の妥当性**: Gemini API のレスポンスが安定して 30 秒以内に返るか未確認。問題が続く場合はタイムアウト値を調整する
- **YouTube URL 機能**: フロントエンドから非表示にしたが、バックエンドの `POST /api/v1/upload/youtube` エンドポイントは残存。将来的に対応する場合は Cookie 認証（`YOUTUBE_COOKIES_B64`）の仕組みを実装済み
- **Supabase 本番 RLS**: ダッシュボードで RLS が有効になっているか目視確認を推奨
- **ローカルSupabase起動不可（開発環境固有の問題）**: このマシンではWindows/DockerのポートbindingがHyper-V/WSLの動的ポート予約と衝突し、`supabase start`がポート`54322`で失敗する。マイグレーションのローカル`db reset`検証ができないため、今後も新規マイグレーション追加時はSQL構文を目視で慎重に確認する必要がある
