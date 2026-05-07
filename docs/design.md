[[requirements]]
# 設計書
## MHWilds ダメージ解析 Webアプリケーション

**バージョン** 1.1　|　**作成日** 2025年　|　**ステータス** Draft

> **v1.1 変更点：** データベースを Supabase（PostgreSQL）に統一。認証も Supabase Auth に移行。

---

## 目次

1. [アーキテクチャ概要](#1-アーキテクチャ概要)
2. [ディレクトリ構成](#2-ディレクトリ構成)
3. [データベース設計](#3-データベース設計)
4. [API設計](#4-api設計)
5. [フロントエンド設計](#5-フロントエンド設計)
6. [バックエンド設計](#6-バックエンド設計)
7. [OCR処理設計](#7-ocr処理設計)
8. [動画処理設計](#8-動画処理設計)
9. [認証設計](#9-認証設計)
10. [シーケンス図](#10-シーケンス図)
11. [エラーハンドリング方針](#11-エラーハンドリング方針)
12. [セキュリティ設計](#12-セキュリティ設計)
13. [環境変数一覧](#13-環境変数一覧)

---

## 1. アーキテクチャ概要

### 1.1 全体構成図

```
╔═══════════════════════════════════════════════════╗
║              ユーザー（ブラウザ）                    ║
╚═══════════════════════╤═══════════════════════════╝
                        │ HTTPS
                        │ ・動画ファイルのアップロード
                        │ ・画面の表示
                        │
╔═══════════════════════▼═══════════════════════════╗
║          フロントエンド（Next.js / Vercel）          ║
║                                                   ║
║  ・動画アップロード画面                              ║
║  ・解析中のリアルタイムログ表示                       ║
║  ・ダメージサマリー画面                              ║
║  ・解析履歴一覧画面                                 ║
╚═══════════════════════╤═══════════════════════════╝
                        │ REST API / SSE
                        │ ・動画データの送信
                        │ ・解析結果のリアルタイム受信
                        │
╔═══════════════════════▼═══════════════════════════╗
║           バックエンド（FastAPI / Render）           ║
║                                                   ║
║  ・動画の受信 → R2 へのストリーミング保存             ║
║  ・FFmpeg による動画→JPEGフレーム変換               ║
║  ・Gemini API を使ったダメージ数値の認識（OCR）       ║
║  ・解析結果の集計・DB保存・SSE配信                   ║
╚═══╤═══════════════════════╤═══════════╤═══════════╝
    │                       │           │
    │ OCR リクエスト          │ DB 読み書き │ 動画の保存・取得・削除
    │                       │           │
╔═══▼════════════╗  ╔═══════▼═══════╗  ╔▼══════════════════╗
║  Gemini API    ║  ║   Supabase    ║  ║  Cloudflare R2    ║
║                ║  ║               ║  ║                   ║
║ ・画像からダメージ║  ║ ・ユーザー認証  ║  ║ ・動画ファイルを   ║
║   数値を検出    ║  ║   （Auth）     ║  ║   一時保存        ║
║                ║  ║ ・解析セッション ║  ║   （処理後削除）  ║
║ ↓ 将来         ║  ║   ダメージログ  ║  ║                   ║
║ Fine-tuned     ║  ║   を保存（DB） ║  ║                   ║
║ Model へ移行   ║  ║               ║  ║                   ║
╚════════════════╝  ╚═══════════════╝  ╚═══════════════════╝
```

### 1.2 通信方式

| 通信 | 方式 | 用途 |
|---|---|---|
| フロント → バックエンド（アップロード） | `multipart/form-data` POST | 動画ファイル送信 |
| フロント → バックエンド（YouTube） | JSON POST | YouTube URL 送信 |
| バックエンド → フロント（進捗） | SSE（Server-Sent Events） | フレーム処理の逐次結果配信 |
| フロント → バックエンド（結果取得） | REST GET | サマリー・ログ取得 |

---

## 2. ディレクトリ構成

### 2.0 プロジェクトルート

```
mhwilds-damage-analyzer/          # リポジトリルート
├── frontend/                     # Next.js アプリ
├── backend/                      # FastAPI アプリ
├── supabase/                     # Supabase CLI が管理するディレクトリ
│   ├── config.toml               # ローカル Supabase の設定
│   ├── migrations/               # マイグレーションファイル（時系列管理）
│   │   ├── 20250401000000_create_analysis_sessions.sql
│   │   └── 20250401000001_create_damage_logs.sql
│   └── seed.sql                  # 開発用初期データ（任意）
└── .env.local                    # ローカル開発用環境変数（Git管理外）
```

> **Supabase ローカル開発について**
> 
> `supabase/` ディレクトリは `supabase init` で自動生成される。ローカルでは Docker 上に PostgreSQL・Auth・Studio が起動し、本番と同じ環境で開発できる。主なコマンドは `supabase start`（起動）・`supabase stop`（停止）・`supabase db reset`（マイグレーション再実行）・`supabase db push`（本番適用）。
> 
> ローカル起動時の接続先（`.env.local` に設定）：
> 
> | 変数 | ローカル値 |
> |---|---|
> | `SUPABASE_URL` | `http://localhost:54321` |
> | `SUPABASE_ANON_KEY` | `supabase start` 実行時に表示される anon key |
> | `SUPABASE_SERVICE_ROLE_KEY` | `supabase start` 実行時に表示される service_role key |
> | `SUPABASE_JWT_SECRET` | `supabase start` 実行時に表示される JWT secret |

### 2.1 フロントエンド（Next.js）

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx               # 共通レイアウト
│   │   ├── page.tsx                 # トップ（アップロード画面）
│   │   ├── analysis/
│   │   │   └── [sessionId]/
│   │   │       └── page.tsx         # ダメージログ + サマリー画面
│   │   ├── history/
│   │   │   └── page.tsx             # 解析履歴一覧（ログイン必須）
│   │   └── auth/
│   │       ├── login/page.tsx
│   │       └── signup/page.tsx
│   ├── components/
│   │   ├── upload/
│   │   │   ├── UploadDropzone.tsx   # ドラッグ&ドロップ
│   │   │   └── VideoUrlInput.tsx    # 動画URL入力
│   │   ├── analysis/
│   │   │   ├── DamageLogViewer.tsx  # ログ一覧（スクロール）
│   │   │   ├── SummaryCard.tsx      # 統計サマリー
│   │   │   └── ExportButton.tsx     # CSV/JSONエクスポート
│   │   └── common/
│   │       ├── Header.tsx
│   │       ├── AuthGuard.tsx
│   │       ├── LoadingSpinner.tsx   # 共通ローディング表示
│   │       └── ProgressBar.tsx      # 共通進捗バー
│   ├── lib/
│   │   ├── api.ts                   # FastAPI クライアント関数
│   │   ├── sse.ts                   # SSE 受信ユーティリティ
│   │   ├── supabase.ts              # Supabase クライアント初期化
│   │   └── auth.ts                  # Supabase Auth ヘルパー
│   └── types/
│       └── index.ts                 # 共通型定義
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

### 2.2 バックエンド（FastAPI）

```
backend/
├── app/
│   ├── main.py                  # エントリーポイント
│   ├── api/
│   │   └── v1/
│   │       ├── upload.py        # 動画アップロードエンドポイント
│   │       ├── analysis.py      # 解析実行・SSE配信
│   │       ├── results.py       # 結果取得エンドポイント
│   │       └── history.py       # 解析履歴エンドポイント
│   ├── services/
│   │   ├── video.py             # FFmpeg 動画処理
│   │   ├── r2.py                # Cloudflare R2 アップロード・削除
│   │   ├── ocr/
│   │   │   ├── base.py          # OCRインターフェース（抽象基底クラス）
│   │   │   ├── gemini.py        # Gemini API 実装
│   │   │   └── custom_model.py  # カスタムモデル実装（将来）
│   │   └── aggregator.py        # ダメージ集計ロジック
│   ├── db/
│   │   └── supabase.py          # Supabase クライアント初期化・クエリ関数
│   ├── schemas/
│   │   └── analysis.py          # Pydantic スキーマ
│   └── core/
│       ├── config.py            # 環境変数・設定
│       └── security.py          # レートリミット等
├── tests/
├── requirements.txt
└── Dockerfile
```

---

## 3. データベース設計

> **Supabase（PostgreSQL）** を使用する。ユーザー管理は **Supabase Auth** が自動生成する `auth.users` テーブルに委譲し、アプリ側では `auth.users.id` を外部キーとして参照する。

### 3.1 テーブル一覧

#### `analysis_sessions` テーブル

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` | セッションID |
| `user_id` | UUID | FK (auth.users.id), NULL許容 | 未ログイン時はNULL |
| `video_name` | TEXT | | 動画ファイル名 / YouTube URL |
| `video_source` | TEXT | CHECK (`file` or `youtube`) | 動画ソース種別 |
| `status` | TEXT | CHECK (`pending` \| `processing` \| `done` \| `error`) | 処理状態 |
| `total_damage` | BIGINT | | 総ダメージ合計 |
| `max_damage` | INT | | 最大単発ダメージ |
| `avg_damage` | FLOAT8 | | 平均ダメージ |
| `hit_count` | INT | | ヒット数 |
| `created_at` | TIMESTAMPTZ | `now()` | 作成日時 |
| `completed_at` | TIMESTAMPTZ | | 処理完了日時 |

#### `damage_logs` テーブル

| カラム名 | 型 | 制約 | 説明 |
|---|---|---|---|
| `id` | BIGINT | PK, `GENERATED ALWAYS AS IDENTITY` | ログID |
| `session_id` | UUID | FK (analysis_sessions.id), ON DELETE CASCADE | セッションID |
| `timestamp_ms` | BIGINT | NOT NULL | 動画内のタイムスタンプ（ミリ秒） |
| `damage_value` | INT | NOT NULL | 検出ダメージ値 |
| `frame_index` | INT | | フレーム番号（デバッグ用） |

### 3.2 DDL（`supabase/migrations/` に配置）

DDL は `supabase/migrations/` 配下に時系列のファイル名で配置し、`supabase db reset` で適用する。テーブル・インデックスは上記テーブル定義の通りに実装する。

### 3.3 Row Level Security（RLS）ポリシー

Supabase の RLS を有効化し、データアクセスをユーザー単位に制限する。

- `public.analysis_sessions`：`auth.uid() = user_id` のセッションのみ参照可
- `public.damage_logs`：上記セッションに紐づくログのみ参照可
- バックエンドは Service Role Key を使用することで RLS をバイパスして全操作可能

> **補足：** 未ログインセッション（`user_id = NULL`）のデータは RLS で保護せず、バックエンドの Service Role Key 経由でのみアクセスする。フロントエンドから直接 Supabase を参照する場合は anon キーを使用し、RLS で保護されたデータのみ返す。

---

## 4. API設計

### 4.1 エンドポイント一覧

#### 動画アップロード

```
POST /api/v1/upload/file
Content-Type: multipart/form-data
Body: { video: <File> }

Response 202:
{
  "session_id": "uuid-xxxx",
  "status": "pending"
}
```

```
POST /api/v1/upload/youtube
Content-Type: application/json
Body: { "url": "https://www.youtube.com/watch?v=xxxx" }

Response 202:
{
  "session_id": "uuid-xxxx",
  "status": "pending"
}
```

#### 解析進捗（SSE）

```
GET /api/v1/analysis/{session_id}/stream
Accept: text/event-stream

# イベント形式
event: damage
data: {"timestamp_ms": 3200, "damage_value": 450, "progress": 12}

event: done
data: {"total_damage": 128400, "hit_count": 312, ...}

event: error
data: {"message": "OCR処理中にエラーが発生しました"}
```

#### 結果取得

```
GET /api/v1/results/{session_id}/summary
Response 200:
{
  "session_id": "uuid-xxxx",
  "total_damage": 128400,
  "max_damage": 1200,
  "avg_damage": 411.5,
  "hit_count": 312,
  "status": "done"
}

GET /api/v1/results/{session_id}/logs?page=1&limit=100
Response 200:
{
  "logs": [
    { "timestamp_ms": 3200, "damage_value": 450 },
    ...
  ],
  "total": 312
}

GET /api/v1/results/{session_id}/export?format=csv
GET /api/v1/results/{session_id}/export?format=json
```

#### 解析履歴（要認証）

```
GET /api/v1/history?page=1&limit=20
Authorization: Bearer <token>
Response 200:
{
  "sessions": [
    {
      "id": "uuid-xxxx",
      "video_name": "hunt_20250401.mp4",
      "total_damage": 128400,
      "created_at": "2025-04-01T10:00:00Z"
    }
  ],
  "total": 35
}
```

---

## 5. フロントエンド設計

### 5.1 画面遷移図

```
[トップ / アップロード画面]
    ├─ ファイル選択 or D&D
    ├─ YouTube URL 入力
    └─ アップロード実行
         │
         ▼
[解析中画面（同一ページ内）]
    ├─ プログレスバー
    ├─ リアルタイムでダメージログが流れる
    └─ 処理完了
         │
         ▼
[ダメージログ + サマリー画面 /analysis/{sessionId}]
    ├─ 統計サマリーカード（総ダメージ・最大・平均・ヒット数）
    ├─ ダメージログ一覧（スクロール）
    └─ エクスポートボタン（CSV / JSON）

[ヘッダー]
    ├─ ログイン / サインアップ（未認証時）
    └─ 解析履歴 / ログアウト（認証済み時）

[解析履歴 /history] ← ログイン必須
    └─ 過去セッション一覧 → クリックで結果画面へ
```

### 5.2 状態管理方針

- グローバル状態：React Context（認証状態のみ）
- サーバー状態：React Query（`@tanstack/react-query`）でキャッシュ・再取得管理
- SSE 受信：カスタムフック `useAnalysisStream(sessionId)` に責務を集約。内部で `EventSource` を使い `damage` / `done` / `error` イベントを購読し、ログ・進捗・サマリー・ステータスを管理する

### 5.3 UIコンポーネント設計

#### UploadDropzone

- `react-dropzone` ライブラリを使用
- ファイルバリデーション：拡張子（mp4 / mov / avi）、最大サイズ制限（要検証）
- アップロード完了後、取得した `session_id` を元に `/analysis/{session_id}` へリダイレクト

#### DamageLogViewer

- 仮想スクロール（`@tanstack/react-virtual`）で大量ログに対応
- ログは時系列昇順で表示
- 各行：`MM:SS.mmm　｜　+{damage}` 形式

#### SummaryCard

- 総ダメージを最大フォントで強調表示
- 平均・最大・ヒット数をカード形式で並列表示

---

## 6. バックエンド設計

### 6.1 解析処理フロー

**ファイルアップロードの場合**

```
1. POST /upload/file
   ├─ セッションレコードを DB に作成（status: pending）
   ├─ 受信しながら R2 にストリーミングアップロード（ディスクに書かない）
   └─ session_id をレスポンス返却

2. バックグラウンドタスク起動（FastAPI BackgroundTasks）
   ├─ status を processing に更新
   ├─ R2 から動画をストリームで取得（ダウンロードしない）
   ├─ FFmpeg の stdin に流し込みながら stdout から JPEG を取得
   ├─ JPEG 1枚取得 → メモリ上で Image に変換 → OCR 実行
   │   └─ 検出のたびに damage_logs へ INSERT・SSE で配信
   │   ↑_______________全フレーム分繰り返す_______________↑
   ├─ 全フレーム完了後、サマリー集計・DB 更新
   ├─ status を done に更新
   └─ R2 の動画ファイルを削除

3. GET /analysis/{session_id}/stream（SSE）
   └─ asyncio.Queue を監視し、新規ログを逐次配信
```

**YouTube URL の場合**

```
1. POST /upload/youtube
   ├─ セッションレコードを DB に作成（status: pending）
   └─ session_id をレスポンス返却

2. バックグラウンドタスク起動
   ├─ status を processing に更新
   ├─ yt-dlp で YouTube から動画を R2 にストリーミング保存
   └─ 保存完了後、ファイルアップロードの 2 と同じ処理へ
      （R2 から取得 → FFmpeg → OCR → 削除）
```

### 6.2 Supabase クライアント（バックエンド）

バックエンドでは `supabase-py` を使い **Service Role Key** でアクセスする（RLS バイパス）。セッションの作成・更新・ダメージログの INSERT などをここに集約する。

### 6.3 非同期処理戦略

- FastAPI の `BackgroundTasks` でシンプルに実装（MVP）
- スケール時は Celery + Redis へ移行を検討
- SSE はセッションごとに `asyncio.Queue` を使いフレーム結果をプッシュ

---

## 7. OCR処理設計

### 7.1 インターフェース定義（抽象クラス）

`OCRServiceBase` を抽象基底クラスとして定義し、`recognize(frame: Image)` メソッドを実装する。戻り値は `OCRResult`（検出ダメージ値のリストと信頼度）。

### 7.2 Gemini API 実装（MVP）

`GeminiOCRService` が `OCRServiceBase` を実装する。フレーム画像を Gemini Vision API に送信し、「ダメージ数値を JSON 形式で返す」よう指示するプロンプトを使用する。レスポンスは `{"damages": [数値, ...]}` 形式でパースする。

### 7.3 フレームサンプリング戦略

- 全フレームを処理するのではなく、一定間隔でサンプリング
- デフォルト：**2fps**（0.5秒ごとに1フレーム）でOCR実行
- ダメージ表示の持続時間（通常0.5〜1秒程度）に合わせて調整
- 重複検出の排除：連続する同一数値・タイムスタンプは1件として記録

### 7.4 将来のモデル切り替え

`OCRServiceBase` を実装するクラスを差し替えるだけで切り替え可能。環境変数 `OCR_BACKEND`（`gemini` または `finetuned`）によって起動時に使用するクラスを切り替える。

---

## 8. 動画処理設計

### 8.1 ストリーミング処理の全体像

動画ファイルは最大 5〜7 GB になるため、**ディスクへの書き込みを一切行わない**ストリーミング処理を採用する。動画は R2 に一時保存し、フレーム画像はメモリ上のみで扱う。

```
R2                  FFmpeg              FastAPI（OCR処理）
┌──────┐            ┌──────────┐        ┌──────────────┐
│動画  │ →ストリーム→ │ stdin    │        │              │
│ファイル│            │          │        │ SOI〜EOI で  │
│      │            │ 動画→JPEG│→stdout→│ 1枚ずつ切り出し│
│      │            │ に変換   │        │      ↓       │
└──────┘            └──────────┘        │ PIL Image に │
                                        │ 変換（メモリ）│
                                        │      ↓       │
                                        │ Gemini OCR   │
                                        │      ↓       │
                                        │ DB 保存・SSE  │
                                        └──────────────┘
```

### 8.2 R2 ファイル管理

R2 には**動画ファイルのみ**を保存する。フレーム画像は R2 に保存しない。

**保存先のパス構成**

```
r2://bucket-name/
└── tmp/
    └── {session_id}/
        └── video.mp4     # アップロード動画 or YouTube DL 動画のみ
```

**R2 操作（`boto3` で S3 互換 API を使用）**

`boto3` を使用し、`upload_fileobj`（ストリーミングアップロード）・`get_object`（ストリーム取得）・`delete_object`（削除）の3操作を `services/r2.py` に集約する。

### 8.3 FFmpeg ストリーミング処理

R2 から取得したストリームを FFmpeg の stdin に流し込み、stdout から JPEG を1枚ずつ取り出す。

- R2 ストリームを別スレッドで FFmpeg の stdin に 1MB ずつ書き込む
- FFmpeg の stdout を読み取り、SOI（`FF D8`）〜 EOI（`FF D9`）マーカーで JPEG を1枚ずつ切り出す
- 切り出した JPEG バイト列をメモリ上で `PIL.Image` に変換し、そのまま OCR に渡す
- 処理完了後（正常・異常問わず）、`finally` ブロックで R2 の動画ファイルを削除する

### 8.4 YouTube 動画取得

`yt-dlp` で YouTube から動画を取得し、R2 にストリーミング保存する。画質は 720p 以下を優先。保存完了後は 8.3 と同じフローで処理する。

---

## 9. 認証設計

> ユーザー認証は **Supabase Auth** に完全委譲する。カスタムの JWT 発行・パスワードハッシュ処理・`users` テーブル管理は不要になる。

### 9.1 フロントエンド（Supabase Auth + Next.js）

- `@supabase/supabase-js` と `@supabase/ssr` を使用
- Supabase Auth のセッションを Cookie に保存し、Next.js Middleware で保護ルートを制御
- 主な操作：`signUp`（サインアップ）・`signInWithPassword`（ログイン）・`signOut`（ログアウト）・`getSession`（セッション取得）
- `/history` は Middleware で認証チェックし、未認証の場合は `/auth/login` にリダイレクト

### 9.2 バックエンド（FastAPI）との連携

フロントエンドから FastAPI へのリクエスト時、Supabase が発行した **Access Token（JWT）** を `Authorization: Bearer` ヘッダーに付与する。FastAPI 側は `SUPABASE_JWT_SECRET` でトークンを検証し `user_id` を取得するだけでよく、独自の認証エンドポイントは不要。トークンがない場合は `None` を返し、未ログインユーザーも利用可能な設計とする。

### 9.3 認証フロー

```
1. ユーザーがメール+パスワードでログイン
   └─ supabase.auth.signInWithPassword() を呼び出し
   └─ Supabase が Access Token + Refresh Token を返す
   └─ Cookie に保存（@supabase/ssr が自動管理）

2. フロントエンドが FastAPI へリクエスト
   └─ Authorization: Bearer <access_token> を付与

3. FastAPI がトークンを検証
   └─ SUPABASE_JWT_SECRET で署名検証
   └─ user_id（sub クレーム）を取得し処理に利用

4. アクセストークン期限切れ時
   └─ Supabase クライアントが自動的に Refresh Token で更新
```

### 9.4 廃止となる実装（旧設計との比較）

| 旧設計 | Supabase Auth 採用後 |
|---|---|
| `users` テーブル（アプリ管理） | `auth.users`（Supabase 管理） |
| `bcrypt` パスワードハッシュ | Supabase が内部で処理 |
| `python-jose` で JWT 発行 | Supabase が発行、FastAPI は検証のみ |
| `POST /api/v1/auth/signup` | Supabase クライアントを直接呼び出し |
| `POST /api/v1/auth/login` | Supabase クライアントを直接呼び出し |
| NextAuth.js | 不要（Supabase Auth に統一） |

---

## 10. シーケンス図

### 10.1 動画アップロード〜解析完了

```
User        Frontend        Backend         FFmpeg       Gemini API    DB
 |              |               |               |              |         |
 |--[ファイル選択]-->|               |               |              |         |
 |              |--POST /upload-->|               |              |         |
 |              |               |--INSERT session(pending)----->|         |
 |              |<--{session_id}--|               |              |         |
 |              |--[SSE接続]----->|               |              |         |
 |              |               |--[BGタスク起動]->|              |         |
 |              |               |               |--フレーム抽出-->|         |
 |              |               |               |<--frame_*.png--|         |
 |              |               |               |              |         |
 |              |               |<--frame_001.png(ループ)        |         |
 |              |               |--認識リクエスト---------------->|         |
 |              |               |<--{damages:[450]}-------------|         |
 |              |               |--INSERT damage_log----------->|         |
 |              |<--SSE damage event--|           |              |         |
 |<--[ログ表示]--|               |               |              |         |
 |              |      ... (繰り返し) ...          |              |         |
 |              |               |--UPDATE session(done)-------->|         |
 |              |<--SSE done event----|           |              |         |
 |<--[サマリー表示]|               |               |              |         |
```

---

## 11. エラーハンドリング方針

| エラー種別 | 対応 |
|---|---|
| 非対応ファイル形式 | フロントエンドでバリデーション、アップロード前にエラー表示 |
| ファイルサイズ超過 | フロントエンド + バックエンド両側でチェック |
| YouTube URL 不正 | バックエンドで検証し 400 エラーを返却 |
| Gemini API エラー | リトライ（最大3回、指数バックオフ）後に SSE `error` イベント配信 |
| FFmpeg 処理失敗 | セッションを `error` 状態に更新、SSE `error` イベント配信 |
| 認証エラー | 401 を返却、フロントエンドでログイン画面へリダイレクト |

---

## 12. セキュリティ設計

### 12.1 レートリミット

- `slowapi`（FastAPI用）を使用
- アップロードエンドポイント：**10回 / 時 / IP**
- OCR解析エンドポイント：**5回 / 時 / IP**

### 12.2 ファイル検証

- MIMEタイプ検証（`python-magic` を使用）
- 拡張子チェック
- ファイルサイズ上限（バックエンドでも検証）

### 12.3 一時ファイルの安全な管理

- R2 のパスに UUID（session_id）を使用（パス推測不可）
- フレーム画像はディスク・R2 に書き込まず、メモリ上のみで処理
- 処理完了後は R2 の動画ファイルを `finally` ブロックで確実に削除
- R2 バケットはパブリックアクセスを無効化（バックエンドからのみアクセス）

### 12.4 CORS設定

本番環境では `allow_origins` に Vercel のデプロイ URL を明示的に指定する。許可メソッドは `GET` / `POST` のみ、許可ヘッダーは `Authorization` と `Content-Type` に限定する。

---

## 13. 環境変数一覧

### フロントエンド（`.env.local`）

| 変数名 | 説明 |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase プロジェクト URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase 公開 anon キー |
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI バックエンドの URL |

### バックエンド（環境変数 / Render の設定）

| 変数名 | 説明 |
|---|---|
| `SUPABASE_URL` | Supabase プロジェクト URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role キー（**厳重管理**） |
| `SUPABASE_JWT_SECRET` | Supabase JWT シークレット（トークン検証用） |
| `R2_ENDPOINT_URL` | Cloudflare R2 エンドポイント URL |
| `R2_ACCESS_KEY_ID` | R2 アクセスキー ID |
| `R2_SECRET_ACCESS_KEY` | R2 シークレットアクセスキー（**厳重管理**） |
| `R2_BUCKET_NAME` | R2 バケット名 |
| `GEMINI_API_KEY` | Gemini API キー |
| `OCR_BACKEND` | `gemini`（デフォルト）または `finetuned` |
| `MAX_UPLOAD_SIZE_MB` | アップロード上限サイズ（MB） |
| `ALLOWED_ORIGINS` | CORS 許可オリジン（カンマ区切り） |

> `SUPABASE_SERVICE_ROLE_KEY` はバックエンドのみで使用し、フロントエンドには絶対に公開しない。

---

*以上*
