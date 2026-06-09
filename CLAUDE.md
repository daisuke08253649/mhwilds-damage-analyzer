# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MHWilds Damage Analyzer — a web app that analyzes Monster Hunter Wilds gameplay videos to extract and aggregate damage numbers using AI/OCR (Gemini API). Users upload a video file or YouTube URL; the backend streams it through FFmpeg, runs OCR on frames, and delivers results in real-time via SSE.

## Repository Structure

```
mhwilds-damage-analyzer/
├── frontend/       # Next.js app (deployed to Vercel)
├── backend/        # FastAPI app (deployed to Render)
├── supabase/       # Supabase CLI config and migrations
├── docs/           # Design and requirements docs
└── .env.local      # Local environment variables (not committed)
```

## Commands

### Frontend (`frontend/`)

```bash
npm run dev      # Start dev server at http://localhost:3000
npm run build    # Production build
npm run lint     # Run ESLint
```

### Backend (`backend/`)

```bash
source .venv/bin/activate     # macOS / Linux
.venv\Scripts\activate        # Windows
pip install -r requirements.txt   # First time only
uvicorn app.main:app --reload     # Dev server at http://localhost:8000
pytest tests/                     # Run tests
```

### Supabase (from repo root)

> **Prerequisites**: Docker Desktop must be installed and running.

```bash
supabase start      # Start local Supabase (Docker required)
supabase stop
supabase db reset   # Re-run all migrations + seed
supabase db push    # Apply migrations to production
```

### Initial Setup — `.env.local`

```bash
cp .env.example .env.local
```

After `supabase start`, fill in the printed keys. See the table below for all variables and where to get them.

| Variable                                                                           | Used by  | Source                                           |
| ---------------------------------------------------------------------------------- | -------- | ------------------------------------------------ |
| `NEXT_PUBLIC_SUPABASE_URL`                                                         | Frontend | `supabase start` output                          |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY`                                                    | Frontend | `supabase start` output                          |
| `NEXT_PUBLIC_API_BASE_URL`                                                         | Frontend | FastAPI local URL                                |
| `SUPABASE_URL`                                                                     | Backend  | `supabase start` output                          |
| `SUPABASE_SERVICE_ROLE_KEY`                                                        | Backend  | `supabase start` output                          |
| `SUPABASE_JWT_SECRET`                                                              | Backend  | `supabase start` output                          |
| `R2_ENDPOINT_URL` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET_NAME` | Backend  | Cloudflare dashboard                             |
| `OPENROUTER_API_KEY`                                                               | Backend  | [OpenRouter](https://openrouter.ai/)             |
| `OPENROUTER_MODEL`                                                                 | Backend  | `google/gemma-4-26b-a4b-it:free` (default)       |
| `OCR_BACKEND`                                                                      | Backend  | `openrouter` (default) or `finetuned`            |

## Architecture

### Data Flow

1. User uploads video file or YouTube URL via the frontend
2. Frontend POSTs to FastAPI → receives `session_id` → immediately opens SSE stream
3. FastAPI creates a DB session record, uploads the video to **Cloudflare R2** (streaming, no disk writes), then starts a background task
4. Background task: R2 → FFmpeg stdin → JPEG frames from stdout → Gemini OCR → INSERT to `damage_logs` + push to SSE queue
5. SSE stream delivers `damage` events (incremental) and a final `done` event with summary stats
6. After processing, R2 video file is deleted in a `finally` block

### Key Design Decisions

- **No disk writes for frames**: frames are kept in memory only (SOI–EOI JPEG marker splitting from FFmpeg stdout)
- **OCR is pluggable**: `OCRServiceBase` in `app/services/ocr/base.py`; switch via `OCR_BACKEND` env var (`gemini` or `finetuned`)
- **Auth is optional**: all features work without login; JWT verified if present, `None` if absent. Logged-in users get results persisted to DB
- **RLS**: frontend uses anon key (RLS enforced); backend uses Service Role key (RLS bypassed). Never expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend
- **Rate limiting**: `slowapi` — 10 uploads/hour/IP, 5 OCR analyses/hour/IP
- **Next.js version**: check `frontend/package.json`. Refer to the [official docs](https://nextjs.org/docs) — do not rely on training data
- **Gemini OCR prompt**: expects `{"damages": [number, ...]}` JSON from frame images
- **Background tasks**: MVP uses FastAPI `BackgroundTasks`; SSE uses `asyncio.Queue` per session
- **Frame sampling**: OCR runs at 2fps (every 0.5s). Consecutive duplicate damage values are deduplicated

### Video Upload Constraints

Accepted formats: MP4, MOV, AVI — Max length: 50 min — File size limit: TBD. Enforced on both frontend (dropzone) and backend (`python-magic` MIME check).

### Frontend Pages (App Router)

| Route                         | Purpose                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------ |
| `/`                           | Upload dropzone + YouTube URL input                                                              |
| `/analysis/[sessionId]`       | Real-time damage log + summary (SSE consumer)                                                    |
| `/history`                    | Past sessions list — protected by `middleware.ts`, redirects to `/auth/login` if unauthenticated |
| `/auth/login`, `/auth/signup` | Supabase Auth email/password                                                                     |

### Backend API Endpoints

| Endpoint                                   | Description                                  |
| ------------------------------------------ | -------------------------------------------- |
| `POST /api/v1/upload/file`                 | Multipart video upload                       |
| `POST /api/v1/upload/youtube`              | YouTube URL submission                       |
| `GET /api/v1/analysis/{session_id}/stream` | SSE stream of damage events                  |
| `GET /api/v1/results/{session_id}/summary` | Final summary stats                          |
| `GET /api/v1/results/{session_id}/logs`    | Paginated damage log                         |
| `GET /api/v1/results/{session_id}/export`  | CSV or JSON export                           |
| `GET /api/v1/history`                      | User's past sessions (requires Bearer token) |

### Database Tables

- `analysis_sessions` — one row per run; status (`pending` → `processing` → `done` / `error`), summary stats, optional `user_id`
- `damage_logs` — one row per hit; `timestamp_ms`, `damage_value`, `frame_index`, FK to `analysis_sessions`

### SSE Event Schema

```
event: damage
data: {"timestamp_ms": 3200, "damage_value": 450, "progress": 12}

event: done
data: {"total_damage": 128400, "max_damage": 1200, "avg_damage": 411.5, "hit_count": 312}

event: error
data: {"message": "OCR processing failed after 3 retries"}
```

`progress` is 0–100. Handle all three events in `useAnalysisStream()`. Close `EventSource` on `done` or `error`.

### R2 Storage Layout

```
r2://<bucket>/tmp/{session_id}/video.mp4
```

Frames are never written to R2. All R2 ops via `app/services/r2.py` (`boto3` S3-compatible API). Bucket is public-access disabled.

## Coding Conventions

### TypeScript (Frontend)

- `strict` mode required in `tsconfig.json`; no `any`
- Explicit types on all function args and return values; shared types in `types/index.ts`
- `interface` for object shapes, `type` for unions; `async/await` over `.then()`

### Python (Backend)

- Type hints required on all function signatures
- `async def` for all route handlers and service functions
- Pydantic models from `schemas/` for all request/response bodies; no raw `dict`
- Import order: stdlib → third-party → internal (`app/`)

## Do Not

| #   | Do NOT                                                                    |
| --- | ------------------------------------------------------------------------- |
| 1   | Write video frames to disk or to R2 — memory only                         |
| 2   | Expose `SUPABASE_SERVICE_ROLE_KEY` to the frontend                        |
| 3   | Commit directly to `main` — use the `develop` branch                      |
| 4   | Use `localStorage` / `sessionStorage` — SSR incompatible                  |
| 5   | Skip reading `frontend-design/SKILL.md` before writing frontend code      |
| 6   | Skip querying Context7 before implementing with any library               |
| 7   | Delete the R2 video file outside the `finally` block                      |
| 8   | Return Service Role key or JWT secret in any API response                 |
| 9   | Implement auth endpoints in FastAPI — delegate entirely to Supabase Auth  |
| 10  | Use `dict` instead of Pydantic models for FastAPI request/response bodies |

## Error Handling Policy

| Error                              | Where              | Action                                                          |
| ---------------------------------- | ------------------ | --------------------------------------------------------------- |
| Unsupported format / size exceeded | Frontend + Backend | Frontend blocks; backend returns 400 / 413                      |
| Invalid YouTube URL                | Backend            | Return 400                                                      |
| Gemini API error                   | Backend            | Retry ×3 with exponential backoff; SSE `error` on final failure |
| FFmpeg failure                     | Backend            | Set session `status` to `error`; send SSE `error`               |
| Auth error                         | Backend            | Return 401; frontend redirects to `/auth/login`                 |
| R2 failure                         | Backend            | Log error; `finally` block still attempts deletion              |

Unhandled errors: `{"detail": "<message>"}`.

## Plugins / MCP Tools

**Always use both plugins before writing code — never rely on training knowledge alone.**

### Context7

Provides up-to-date official docs for all libraries used in this project (Next.js, FastAPI, Supabase, `@tanstack/*`, `react-dropzone`, etc.).

```
mcp__context7__resolve-library-id: "next.js"
mcp__context7__get-library-docs: <id> topic="app router middleware"
```

### frontend-design

Defines the visual language of this project — colors, spacing, typography, component patterns.

```
view: /mnt/skills/public/frontend-design/SKILL.md
```

Read before creating or editing any component, page, or Tailwind style.

## Development Phases

> Phase 0 (environment setup) is already complete. Start from Phase 1.

| Phase       | Focus                                                                 |
| ----------- | --------------------------------------------------------------------- |
| **Phase 1** | Database: migrations, indexes, RLS policies                           |
| **Phase 2** | Backend: R2, FFmpeg, OCR, aggregator, API endpoints, auth integration |
| **Phase 3** | Frontend: components, pages, SSE hook, auth screens, history page     |
| **Phase 4** | Deploy: Vercel + Render + Supabase production setup                   |
| **Phase 5** | Tests & QA: unit tests, E2E flow, performance, monitoring             |

Implement in order. Do not advance phases without explicit instruction.

## Git Workflow

⚠️ **All implementation must be done in the `develop` branch. Never commit directly to `main`.**

> Always create a new branch for each phase before starting implementation. Never implement multiple phases on the same branch.

### Commit Messages — [Conventional Commits](https://www.conventionalcommits.org/)

| Type    | When                         |
| ------- | ---------------------------- |
| `feat`  | New feature                  |
| `fix`   | Bug fix                      |
| `chore` | Config, deps, docs, refactor |
| `test`  | Tests                        |

Examples: `feat: add upload dropzone` / `fix: deduplicate damage values` / `chore: update dependencies`

### Branch Names

Keep branch names short and concise.

```
feature/upload-dropzone
fix/gemini-retry-on-timeout
chore/add-rate-limit-config
```

### Commit → PR Flow

```bash
git checkout -b feature/your-feature-name
```

After each phase is complete, **always stop and provide a summary of the implementation** in the following format, then notify the user:

```
## Implementation Summary

### Changes
- List of files created or modified

### What was implemented
- Brief description of each change

### How to verify
- Steps to confirm the implementation works correctly
```

> "Implementation is complete. Please share the above summary with OpenCode for a code review. I will wait for the feedback before committing."

Do not run `git add` or `git commit` until the user has shared the OpenCode review results.

Repeat the following cycle until the review returns no issues:

1. Receive OpenCode review feedback from the user
2. Fix all flagged issues
3. Notify the user: "Fixes are complete. Please run the OpenCode review again."
4. Wait for the next review

Once the review returns no issues, commit and push:

```bash
git add . && git commit -m "feat: describe what you implemented"
git push origin feature/your-feature-name
gh pr create --title "feat: ..." --body "## Summary
- What and why

## Changes
- Key changes

## Testing
- How to verify"
```

> `gh` requires [GitHub CLI](https://cli.github.com/) (`gh auth login`). Target branch: `main`.
