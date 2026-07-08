-- 便宜機票平台 — Supabase 資料表 + RLS
-- 用法：Supabase 專案 → SQL Editor → 貼上整段 → Run（執行一次即可）

-- 價格歷史（算基準線用；只有後端 worker 存取，不對外）
create table if not exists public.prices (
  id          bigserial primary key,
  origin      text not null,
  destination text not null,
  price       double precision not null,
  currency    text,
  cabin       text,
  depart_date date,
  source      text,
  observed_at timestamptz default now(),
  airline     text
);
create index if not exists idx_prices_route on public.prices (origin, destination, observed_at);

-- 好康（前端要讀）
create table if not exists public.deals (
  id                 bigserial primary key,
  created_at         timestamptz default now(),
  type               text,
  route_str          text,
  origin             text,
  destination        text,
  price              double precision,
  currency           text,
  cabin              text,
  depart_date        date,
  return_date        date,
  baseline_median    double precision,
  discount_pct       double precision,
  tier               text,
  needs_verification boolean default false,
  reasons            jsonb,
  deep_link          text,
  source             text,
  airline            text,
  flight_number      text,
  transfers          int,
  depart_time        text,
  gate               text,
  dedupe_key         text unique
);
create index if not exists idx_deals_id on public.deals (id desc);

-- 去重
create table if not exists public.deals_seen (
  key text primary key,
  ts  timestamptz default now()
);

-- 裝置 / 訂閱（前端寫入，未來推播用）
create table if not exists public.devices (
  token      text primary key,
  platform   text,
  updated_at timestamptz default now()
);
create table if not exists public.subscriptions (
  device     text primary key,
  routes     jsonb,
  max_price  double precision,
  cabin      text,
  updated_at timestamptz default now()
);

-- === RLS：全部開啟，只開放必要的 anon 權限 ===
alter table public.prices        enable row level security;
alter table public.deals         enable row level security;
alter table public.deals_seen    enable row level security;
alter table public.devices       enable row level security;
alter table public.subscriptions enable row level security;

-- 匿名可讀好康（前端列表）
create policy "anon read deals" on public.deals
  for select to anon using (true);

-- 匿名可寫裝置 / 訂閱（前端註冊與設定；upsert 需要 insert + update）
create policy "anon insert devices" on public.devices
  for insert to anon with check (true);
create policy "anon update devices" on public.devices
  for update to anon using (true) with check (true);

create policy "anon read subs" on public.subscriptions
  for select to anon using (true);
create policy "anon insert subs" on public.subscriptions
  for insert to anon with check (true);
create policy "anon update subs" on public.subscriptions
  for update to anon using (true) with check (true);

-- 註：prices / deals_seen 不開放 anon；後端 worker 用 DATABASE_URL 連線會繞過 RLS。
