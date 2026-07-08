// 與後端 flightdeals/serializers.py、api/schemas.py 對齊的型別。

export type DealType = "cheap" | "error_fare" | "nested";

export interface Deal {
  id: number;
  created_at: string;
  type: DealType;
  route: { origin: string; destination: string };
  route_str: string;
  price: number;
  currency: string;
  cabin: string;
  depart_date: string | null;
  return_date: string | null;
  baseline_median: number;
  discount_pct: number; // 0~1
  tier: string;
  needs_verification: boolean;
  reasons: string[];
  deep_link: string | null;
  source: string;
  airline?: string | null;
  flight_number?: string | null;
  depart_time?: string | null; // "HH:MM"
  transfers?: number | null; // 0=直飛
  gate?: string | null; // 開這個價的訂票網站（如 Trip.com / Kiwi.com）
}

export interface RouteInfo {
  origin: string;
  destination: string;
  label: string;
}

export interface Subscription {
  device: string;
  routes: string[];
  max_price: number | null;
  cabin: string | null;
}
