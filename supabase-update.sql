alter table public.users
add column if not exists has_seen_tour boolean not null default false;

create policy if not exists "Users can update own tour preference"
  on public.users
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);
