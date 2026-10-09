-- Run this in Supabase Dashboard → SQL Editor → New query.
create table if not exists public.books (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  author text,
  status text not null default 'want' check (status in ('want','reading','read')),
  rating smallint not null default 0 check (rating between 0 and 5),
  notes text not null default '',
  synopsis text not null default '',
  cover_id bigint,
  cover_url text,
  openlibrary_key text,
  published_year integer,
  created_at timestamptz not null default now()
);
create index if not exists books_user_created_idx on public.books(user_id, created_at desc);
alter table public.books enable row level security;
-- Each signed-in user can access only their own records.
drop policy if exists "Users can read their own books" on public.books;
create policy "Users can read their own books" on public.books for select to authenticated using (auth.uid() = user_id);
drop policy if exists "Users can add their own books" on public.books;
create policy "Users can add their own books" on public.books for insert to authenticated with check (auth.uid() = user_id);
drop policy if exists "Users can update their own books" on public.books;
create policy "Users can update their own books" on public.books for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);
drop policy if exists "Users can delete their own books" on public.books;
create policy "Users can delete their own books" on public.books for delete to authenticated using (auth.uid() = user_id);
