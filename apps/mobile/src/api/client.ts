import { SUPABASE_ANON_KEY, SUPABASE_URL } from "../config";
import type { Deal, RouteInfo, Subscription } from "./types";

// 前端直接打 Supabase 的 PostgREST 自動 API（不需要自己的後端伺服器）
const REST = `${SUPABASE_URL}/rest/v1`;
const baseHeaders: Record<string, string> = {
  apikey: SUPABASE_ANON_KEY,
  Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
  "Content-Type": "application/json",
};

async function rest<T>(path: string, init?: RequestInit): Promise<T> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error("尚未設定 Supabase（EXPO_PUBLIC_SUPABASE_URL / EXPO_PUBLIC_SUPABASE_ANON_KEY）");
  }
  const res = await fetch(`${REST}${path}`, {
    ...init,
    headers: { ...baseHeaders, ...((init?.headers as Record<string, string>) ?? {}) },
  });
  if (!res.ok) throw new Error(`Supabase ${res.status}：${await res.text()}`);
  const text = await res.text();
  return (text ? JSON.parse(text) : null) as T;
}

// Supabase deals 表回傳的是扁平欄位；轉成 App 的 Deal 型別
type DealRow = Omit<Deal, "route"> & { origin: string; destination: string };
function toDeal(r: DealRow): Deal {
  const { origin, destination, ...rest } = r;
  return { ...rest, route: { origin, destination } } as Deal;
}

// 航線清單前端固定（與後端 config 一致；未來要動態可改讀一張 routes 表）
const ROUTES: RouteInfo[] = (
  [["TPE", "NRT"], ["TPE", "KIX"], ["TPE", "ICN"], ["TPE", "BKK"], ["TPE", "DAD"], ["TPE", "CDG"], ["TPE", "LHR"]] as const
).map(([o, d]) => ({ origin: o, destination: d, label: `${o}→${d}` }));

export const api = {
  routes: async (): Promise<RouteInfo[]> => ROUTES,

  deals: async (type?: string, limit = 50): Promise<Deal[]> => {
    const filter = type ? `&type=eq.${encodeURIComponent(type)}` : "";
    const rows = await rest<DealRow[]>(`/deals?select=*&order=id.desc&limit=${limit}${filter}`);
    return (rows ?? []).map(toDeal);
  },

  deal: async (id: number): Promise<Deal> => {
    const rows = await rest<DealRow[]>(`/deals?select=*&id=eq.${id}`);
    if (!rows || rows.length === 0) throw new Error("找不到這筆好康");
    return toDeal(rows[0]);
  },

  registerDevice: (token: string, platform: string) =>
    rest("/devices?on_conflict=token", {
      method: "POST",
      headers: { Prefer: "resolution=merge-duplicates" },
      body: JSON.stringify({ token, platform }),
    }),

  getSubscription: async (device: string): Promise<Subscription> => {
    const rows = await rest<Subscription[]>(
      `/subscriptions?select=*&device=eq.${encodeURIComponent(device)}`
    );
    return (rows && rows[0]) ?? { device, routes: [], max_price: null, cabin: null };
  },

  setSubscription: (sub: Subscription) =>
    rest("/subscriptions?on_conflict=device", {
      method: "POST",
      headers: { Prefer: "resolution=merge-duplicates" },
      body: JSON.stringify(sub),
    }),
};
