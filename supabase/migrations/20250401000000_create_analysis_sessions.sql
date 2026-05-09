create table public.analysis_sessions (
    id             uuid        primary key default gen_random_uuid(),
    user_id        uuid        references auth.users(id) on delete set null,
    video_name     text,
    video_source   text        check (video_source in ('file', 'youtube')),
    status         text        not null default 'pending'
                                check (status in ('pending', 'processing', 'done', 'error')),
    total_damage   bigint,
    max_damage     int,
    avg_damage     float8,
    hit_count      int,
    created_at     timestamptz not null default now(),
    completed_at   timestamptz
);

create index idx_analysis_sessions_user_id on public.analysis_sessions (user_id);

alter table public.analysis_sessions enable row level security;

create policy "Users can view own sessions"
    on public.analysis_sessions
    for select
    using ((select auth.uid()) = user_id);
