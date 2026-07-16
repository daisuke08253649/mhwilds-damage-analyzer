## 実装進捗サマリー

最終更新: 2026-07-14

### ✅ 完了済みのタスク

`tasks.md` の Phase 0〜4 は全項目完了。Phase 5（テスト・品質保証）はユニットテストと本番バグ修正まで完了。

- **Phase 0〜4**: モノレポ構成・DB/RLS・バックエンド全機能・フロントエンド全画面・Vercel/Render/Supabase本番デプロイ、すべて完了済み
  - Render: https://mhwilds-damage-analyzer.onrender.com
  - Vercel: https://mhwilds-damage-analyzer.vercel.app
- **Phase 5（進行中）**:
  - ユニットテスト全パス確認済み（backend: 38件）
  - 本番環境で発生した各種バグ（CORS、Supabase接続、yt-dlp/Node.js、SSE安定性等）は順次修正済み
- **Supabase 非アクティブ停止対策**（2026-07-14 完了・動作確認済み）
  - GAS から Supabase REST API (PostgREST) に直接 INSERT する `keep_alive_pings` テーブル方式に変更
  - GAS 側の `pingSupabaseKeepAlive` への切り替え・動作確認（`status: 201`、テーブルへの行追加）をユーザーが完了・確認済み
- **Render本番環境のOOM対策**（2026-07-14 実装・レビュー完了・develop/mainへマージ済み）
  - 本番E2Eで動画解析が途中で停止する不具合が発生。原因はOCR前にフレームを元動画解像度のまま未圧縮でメモリ展開していたこと
  - 対応：FFmpegでOCR前にフレームを縮小（`FRAME_MAX_WIDTH`環境変数、デフォルト1280px）、OCR後に`image.close()`で即時解放、キャンセル・例外時のキュー内フレームも確実にclose、ffmpeg stderrの無制限保持を末尾4KBに制限、`FRAME_MAX_WIDTH`起動時バリデーション追加
  - 副次的に発見した既存バグ（`upload.py`で`asyncio`未importによる`NameError`）も修正
  - Codexレビューを複数ラウンド実施し指摘事項を全て反映。テスト38件全てパス
  - PR #11（`fix/render-oom-frame-memory` → `develop`）をマージ → `develop`を`main`にマージ・push済み
- **CLAUDE.mdのGitワークフロー記載を修正**
  - 「PRは`main`ではなく`develop`をターゲットにする」「develop→mainの昇格は最終テスト後に行う」という想定フローに合わせて記載を修正済み

### 🔧 作業中・未完了のタスク

- **本番E2Eフローの再確認（OOM修正後）が未実施**：前回のE2Eで解析途中に停止する不具合が発生し、それを修正した状態。修正後の再検証はまだ行っていない
- Renderのデプロイトリガーが`main`起点か`develop`起点か未確認
- 50分動画でのパフォーマンス・メモリ使用量確認：未着手
- Gemini API消費量モニタリング設定：未着手

### 👉 次のアクション（再開時の起点）

1. Renderのデプロイ設定（デプロイトリガーとなるブランチ）を確認し、今回のOOM修正（`main`へのマージ内容）がRenderに反映されているか確認する
2. 反映されていれば、本番サイト（https://mhwilds-damage-analyzer.vercel.app）で短いMP4を再度アップロードし、
   - 解析が最後まで完了するか
   - Render Dashboard → Metrics でメモリ使用量のピークが以前より下がっているか
   - Render Dashboard → Logs にエラーが出ていないか
   を確認する
3. E2Eが正常に完了した場合：50分動画でのパフォーマンス・メモリ確認、Gemini API消費量モニタリング設定に着手する
4. E2Eでまだ問題が出た場合：Renderのログとブラウザ側のSSEエラーメッセージを確認してから追加調査する

### ⚠️ 懸念事項・確認が必要な点

- 今回のOOM修正（フレーム最大幅1280px、`FRAME_MAX_WIDTH`で調整可）は、実際の本番動画・Render環境ではまだ検証されていない。1280pxが画質・OCR精度とメモリ使用量のバランスとして適切かは、再E2E後に様子を見て要調整
- Renderの自動デプロイトリガーが`main`か`develop`かが未確認のため、次回再開時に最初に確認する必要がある
- develop→mainの昇格は過去の履歴（`Merge branch 'develop'`コミット）に倣い、PRを介さず直接`git merge`で実施している。この運用を続けるかは今後も要確認
- Render 無料プランは15分アクセスがないとスリープする問題は引き続き未解決（許容する方針）。初回アクセス時にコールドスタート待ちが発生し得る
- Gemini API 無料枠は長時間動画で消費量が大きくなる可能性がある（`GEMINI_MODEL`で別モデルへの切り替えは可能）
- ローカルでの Supabase 起動不可の問題（Windows/Docker のポートbinding衝突）は継続中。新規マイグレーション追加時は `supabase db reset` でのローカル検証ができないため、SQL構文を目視で慎重に確認する必要がある
- YouTube URL機能はフロントエンドから非表示にしたままだが、バックエンドの`POST /api/v1/upload/youtube`エンドポイントは残存（Cookie認証の仕組みは実装済み）
