alter table public.analysis_sessions
    drop constraint analysis_sessions_user_id_fkey;

alter table public.analysis_sessions
    add constraint analysis_sessions_user_id_fkey
    foreign key (user_id) references auth.users(id) on delete cascade;
