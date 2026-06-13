create table public.damage_logs (
    id            bigint  generated always as identity primary key,
    session_id    uuid    not null references public.analysis_sessions(id) on delete cascade,
    timestamp_ms  bigint  not null,
    damage_value  int     not null,
    frame_index   int
);

create index idx_damage_logs_session_id on public.damage_logs (session_id);

alter table public.damage_logs enable row level security;

create policy "Users can view logs for own sessions"
    on public.damage_logs
    for select
    using (
        exists (
            select 1
            from public.analysis_sessions
            where analysis_sessions.id = damage_logs.session_id
              and analysis_sessions.user_id = (select auth.uid())
        )
    );
