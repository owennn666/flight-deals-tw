// 卡片與詳情頁共用的 deal 文字組裝邏輯（日期行 / 航班資訊行）。
import type { Deal } from "../api/types";
import { AIRLINE_NAMES } from "../api/client";

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const thisYear = new Date().getFullYear();
  return y === thisYear ? `${m}/${d}` : `${y}/${m}/${d}`;
}

// 日期行：區分來回／單程
export function dateLine(deal: Deal): string | null {
  if (!deal.depart_date) return null;
  if (deal.return_date) return `${fmtDate(deal.depart_date)} – ${fmtDate(deal.return_date)} 來回`;
  return `${fmtDate(deal.depart_date)} 單程`;
}

// 航班資訊行：航空公司／班號／起飛時間／轉機數
export function flightInfoLine(deal: Deal): string | null {
  const parts: string[] = [];
  if (deal.airline) parts.push(`${AIRLINE_NAMES[deal.airline] ?? deal.airline}${deal.flight_number ? ` ${deal.flight_number}` : ""}`);
  else if (deal.flight_number) parts.push(deal.flight_number);
  if (deal.depart_time) parts.push(deal.depart_time);
  if (deal.transfers !== undefined && deal.transfers !== null) {
    parts.push(deal.transfers === 0 ? "直飛" : `轉${deal.transfers}次`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}
