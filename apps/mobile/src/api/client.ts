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

// 廉航 IATA 代碼白名單（「隱藏廉航」篩選用；null/查不到的一律視為非廉航）
export const LCC_AIRLINES: string[] = [
  "SL", "FD", "AK", "D7", "TR", "IT", "VZ", "JW", "XJ", "JQ",
  "5J", "Z2", "DD", "JT", "QZ", "TW", "LJ", "BX", "ZE", "GK", "MM",
];

// 航空公司 IATA 代碼 → 中文名（查不到顯示原代碼）
export const AIRLINE_NAMES: Record<string, string> = {
  SL: "泰國獅航",
  FD: "泰國亞航",
  AK: "亞航",
  D7: "亞航X",
  TR: "酷航",
  IT: "台灣虎航",
  VZ: "泰越捷",
  JX: "星宇航空",
  BR: "長榮航空",
  CI: "中華航空",
  NH: "全日空",
  JL: "日本航空",
  KE: "大韓航空",
  OZ: "韓亞航空",
  TG: "泰航",
  SQ: "新航",
  CX: "國泰",
  MU: "東方航空",
  CA: "國航",
  VN: "越航",
  PR: "菲航",
  "5J": "宿霧太平洋",
  JQ: "捷星",
};

export interface DealsQuery {
  type?: string;
  origin?: string;
  destination?: string;
  minDiscount?: number;
  maxPrice?: number;
  limit?: number;
}

export const api = {
  routes: async (): Promise<RouteInfo[]> => ROUTES,

  deals: async (opts?: DealsQuery): Promise<Deal[]> => {
    const { type, origin, destination, minDiscount, maxPrice, limit = 50 } = opts ?? {};
    let filter = "";
    if (type) filter += `&type=eq.${encodeURIComponent(type)}`;
    if (origin) filter += `&origin=eq.${encodeURIComponent(origin)}`;
    if (destination) filter += `&destination=eq.${encodeURIComponent(destination)}`;
    if (minDiscount !== undefined) filter += `&discount_pct=gte.${minDiscount}`;
    if (maxPrice !== undefined) filter += `&price=lte.${maxPrice}`;
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
