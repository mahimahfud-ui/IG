create extension if not exists pgcrypto;

create table if not exists public.profiles(
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique check(username ~ '^[a-z0-9_.-]{3,24}$'),
  display_name text,
  bio text default 'photographs · motion · moments',
  avatar_url text,
  instagram_url text default 'https://www.instagram.com/mahimahfud/',
  youtube_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.media(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  type text not null check(type in('image','video')),
  storage_path text unique not null,
  thumbnail_path text,
  original_url text not null,
  thumbnail_url text,
  title text,
  caption text,
  mime_type text not null,
  width integer,
  height integer,
  duration numeric,
  file_size bigint not null default 0,
  visibility text not null default 'public' check(visibility in('public','private')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

do $$
begin
  if not exists(select 1 from pg_constraint where conname='media_video_duration_check') then
    alter table public.media add constraint media_video_duration_check
    check(type='image' or (duration is not null and duration >= 0 and duration <= 90));
  end if;
  if not exists(select 1 from pg_constraint where conname='media_video_resolution_check') then
    alter table public.media add constraint media_video_resolution_check
    check(type='image' or (width is not null and height is not null and greatest(width,height) <= 1920 and least(width,height) <= 1080));
  end if;
end$$;

create index if not exists media_user_created_idx on public.media(user_id,created_at desc);
create schema if not exists private;

create table if not exists public.username_reservations(
  username text primary key check(username ~ '^[a-z0-9_.-]{3,24}$'),
  user_id uuid references auth.users(id) on delete set null,
  reserved_at timestamptz not null default now()
);

alter table public.username_reservations enable row level security;
revoke all on public.username_reservations from anon,authenticated;

insert into public.username_reservations(username,user_id)
select lower(username),id from public.profiles
on conflict(username) do nothing;

insert into public.username_reservations(username,user_id)
values('mahimahfud',null)
on conflict(username) do nothing;

create or replace function private.reserve_profile_username()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  existing_user uuid;
begin
  if new.username is null or new.username !~ '^[a-z0-9_.-]{3,24}$' then
    raise exception 'USERNAME_INVALID';
  end if;

  select user_id into existing_user
  from public.username_reservations
  where username = lower(new.username)
  for update;

  if found and existing_user is distinct from new.id then
    raise exception 'USERNAME_TAKEN';
  end if;

  if not found then
    insert into public.username_reservations(username,user_id)
    values(lower(new.username),new.id);
  end if;

  new.username := lower(new.username);
  return new;
exception
  when unique_violation then
    raise exception 'USERNAME_TAKEN';
end;
$$;

revoke all on function private.reserve_profile_username() from public;

drop trigger if exists profiles_username_reserve on public.profiles;
create trigger profiles_username_reserve
before insert on public.profiles
for each row execute function private.reserve_profile_username();

create or replace function private.prevent_username_change()
returns trigger
language plpgsql
as $$
begin
  if new.username is distinct from old.username then
    raise exception 'USERNAME_IMMUTABLE';
  end if;
  return new;
end;
$$;

revoke all on function private.prevent_username_change() from public;

drop trigger if exists profiles_username_immutable on public.profiles;
create trigger profiles_username_immutable
before update of username on public.profiles
for each row execute function private.prevent_username_change();

create or replace function private.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = pg_catalog, public
as $$
declare
  requested_username text;
  display_value text;
begin
  requested_username := lower(trim(coalesce(new.raw_user_meta_data->>'username','')));
  display_value := trim(coalesce(new.raw_user_meta_data->>'display_name',requested_username));

  -- OAuth providers such as Google may not have a user-selected username yet.
  -- In that case the auth account is created first and the app asks for a username after OAuth.
  if requested_username = '' or requested_username !~ '^[a-z0-9_.-]{3,24}$' then
    return new;
  end if;

  insert into public.profiles(id,username,display_name)
  values(new.id,requested_username,coalesce(nullif(display_value,''),requested_username))
  on conflict(id) do nothing;

  return new;
exception
  when unique_violation then
    raise exception 'USERNAME_TAKEN';
end;
$$;

revoke all on function private.handle_new_user() from public;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function private.handle_new_user();

alter table public.profiles enable row level security;
alter table public.media enable row level security;

drop policy if exists profiles_public_read on public.profiles;
create policy profiles_public_read
on public.profiles for select
to anon,authenticated
using(true);

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own
on public.profiles for insert
to authenticated
with check((select auth.uid())=id);

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
on public.profiles for update
to authenticated
using((select auth.uid())=id)
with check((select auth.uid())=id);

drop policy if exists media_public_read on public.media;
create policy media_public_read
on public.media for select
to anon,authenticated
using(visibility='public' or (select auth.uid())=user_id);

drop policy if exists media_insert_own on public.media;
create policy media_insert_own
on public.media for insert
to authenticated
with check((select auth.uid())=user_id);

drop policy if exists media_update_own on public.media;
create policy media_update_own
on public.media for update
to authenticated
using((select auth.uid())=user_id)
with check((select auth.uid())=user_id);

drop policy if exists media_delete_own on public.media;
create policy media_delete_own
on public.media for delete
to authenticated
using((select auth.uid())=user_id);

grant select on public.profiles to anon,authenticated;
grant insert,update on public.profiles to authenticated;
grant select,insert,update,delete on public.media to authenticated;
grant select on public.media to anon,authenticated;

do $$
begin
  if exists(select 1 from pg_publication where pubname='supabase_realtime') then
    begin
      alter publication supabase_realtime add table public.media;
    exception when duplicate_object then
      null;
    end;
  end if;
end$$;

insert into storage.buckets(id,name,public,file_size_limit)
values('media','media',true,536870912)
on conflict(id) do update
set public=true,file_size_limit=536870912;

drop policy if exists media_bucket_insert on storage.objects;
create policy media_bucket_insert
on storage.objects for insert
to authenticated
with check(
  bucket_id='media'
  and (storage.foldername(name))[1]=(select auth.uid()::text)
);

drop policy if exists media_bucket_update on storage.objects;
create policy media_bucket_update
on storage.objects for update
to authenticated
using(
  bucket_id='media'
  and (storage.foldername(name))[1]=(select auth.uid()::text)
)
with check(
  bucket_id='media'
  and (storage.foldername(name))[1]=(select auth.uid()::text)
);

drop policy if exists media_bucket_delete on storage.objects;
create policy media_bucket_delete
on storage.objects for delete
to authenticated
using(
  bucket_id='media'
  and (storage.foldername(name))[1]=(select auth.uid()::text)
);