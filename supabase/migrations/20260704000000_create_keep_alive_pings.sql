create table public.keep_alive_pings (
    id         bigint      generated always as identity primary key,
    pinged_at  timestamptz not null default now()
);

alter table public.keep_alive_pings enable row level security;

create policy "Anyone can insert keep-alive pings"
    on public.keep_alive_pings
    for insert
    to anon
    with check (true);
