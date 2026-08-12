-- Custom table used by the frontend demo auth flow
create table if not exists public.my_users (
  id serial primary key,
  name text not null,
  email text not null unique,
  password text not null,
  created_at timestamp default now()
);

alter table public.my_users disable row level security;

grant select, insert, update, delete on table public.my_users to anon, authenticated;

-- Create the public.users table for Supabase Auth profile data
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  name text,
  avatar text,
  subscription_tier text not null default 'free' check (subscription_tier in ('free', 'pro', 'enterprise')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.users enable row level security;

-- Allow authenticated users to read and update only their own record
create policy if not exists "Users can view own profile"
  on public.users
  for select
  using (auth.uid() = id);

create policy if not exists "Users can insert own profile"
  on public.users
  for insert
  with check (auth.uid() = id);

create policy if not exists "Users can update own profile"
  on public.users
  for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Grant minimal access to authenticated users
grant select, insert, update on public.users to authenticated;

-- Trigger to backfill profile data whenever a new Supabase Auth user is created
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.users (id, email, name, avatar)
  values (
    new.id,
    new.email,
    coalesce(
      new.raw_user_meta_data->>'full_name',
      new.raw_user_meta_data->>'name',
      split_part(new.email, '@', 1)
    ),
    coalesce(
      new.raw_user_meta_data->>'avatar_url',
      new.raw_user_meta_data->>'picture'
    )
  )
  on conflict (id) do update set
    email = excluded.email,
    name = coalesce(excluded.name, public.users.name),
    avatar = coalesce(excluded.avatar, public.users.avatar),
    updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();
