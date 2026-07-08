import React from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";
import type { Deal } from "../api/types";
import { AIRLINE_NAMES } from "../api/client";

function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const thisYear = new Date().getFullYear();
  return y === thisYear ? `${m}/${d}` : `${y}/${m}/${d}`;
}

function dateLine(deal: Deal): string | null {
  if (!deal.depart_date) return null;
  if (deal.return_date) return `${fmtDate(deal.depart_date)} – ${fmtDate(deal.return_date)} 來回`;
  return `${fmtDate(deal.depart_date)} 單程`;
}

function flightInfoLine(deal: Deal): string | null {
  const parts: string[] = [];
  if (deal.airline) parts.push(`${AIRLINE_NAMES[deal.airline] ?? deal.airline}${deal.flight_number ? ` ${deal.flight_number}` : ""}`);
  else if (deal.flight_number) parts.push(deal.flight_number);
  if (deal.depart_time) parts.push(deal.depart_time);
  if (deal.transfers !== undefined && deal.transfers !== null) {
    parts.push(deal.transfers === 0 ? "直飛" : `轉${deal.transfers}次`);
  }
  return parts.length > 0 ? parts.join(" · ") : null;
}

export default function DealCard({ deal, onPress }: { deal: Deal; onPress: () => void }) {
  const isBug = deal.type === "error_fare";
  const flightInfo = flightInfoLine(deal);
  const dates = dateLine(deal);
  const route = deal.route_str.replace("->", " → ");
  const pct = Math.round(deal.discount_pct * 100);
  const median = Math.round(deal.baseline_median).toLocaleString();
  const hint = isBug
    ? `比平常低 ${pct}% · 航司不保證出票，訂票風險自負`
    : `這條航線平常約 ${median}${deal.tier === "strong" ? " · 難得低價" : ""}${deal.gate ? ` · 經 ${deal.gate} 訂` : ""}`;
  const isTrip = deal.gate === "Trip.com" || !deal.gate;
  const buttonLabel = isBug
    ? (isTrip ? "前往 Trip.com 查看 ↗" : "前往 Aviasales 查看 ↗")
    : (isTrip ? "前往 Trip.com 訂票 ↗" : "前往 Aviasales 比價 ↗");

  return (
    <Pressable style={[styles.card, isBug && styles.cardBug]} onPress={onPress}>
      <View style={styles.row}>
        <Text style={[styles.route, isBug && styles.textBug]}>{route}</Text>
        <View style={[styles.pill, isBug ? styles.pillBug : styles.pillGood]}>
          <Text style={[styles.pillText, isBug ? styles.pillTextBug : styles.pillTextGood]}>
            {isBug ? "疑似標錯價" : `比平常低 ${pct}%`}
          </Text>
        </View>
      </View>
      {dates ? <Text style={[styles.dates, isBug && styles.subBug]}>{dates}</Text> : null}
      <Text style={[styles.price, isBug && styles.textBug]}>
        {deal.price.toLocaleString()} <Text style={styles.currency}>{deal.currency}</Text>
      </Text>
      {flightInfo ? <Text style={[styles.sub, isBug && styles.subBug]}>✈ {flightInfo}</Text> : null}
      <Text style={[styles.hint, isBug && styles.subBug]}>{hint}</Text>
      {deal.deep_link ? (
        <Pressable
          style={[styles.button, isBug && styles.buttonBug]}
          onPress={() => Linking.openURL(deal.deep_link as string)}
        >
          <Text style={styles.buttonText}>{buttonLabel}</Text>
        </Pressable>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 14,
    marginHorizontal: 12,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: "#e8e8e8",
  },
  cardBug: { backgroundColor: "#FCEBEB", borderColor: "#F7C1C1" },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  route: { fontSize: 16, fontWeight: "700", color: "#111" },
  textBug: { color: "#A32D2D" },
  pill: { borderRadius: 999, paddingHorizontal: 9, paddingVertical: 3 },
  pillGood: { backgroundColor: "#E1F5EE" },
  pillBug: { backgroundColor: "#fff" },
  pillText: { fontSize: 12, fontWeight: "600" },
  pillTextGood: { color: "#0F6E56" },
  pillTextBug: { color: "#A32D2D" },
  dates: { fontSize: 13, fontWeight: "600", color: "#444", marginTop: 5 },
  price: { fontSize: 24, fontWeight: "800", color: "#111", marginTop: 2 },
  currency: { fontSize: 13, fontWeight: "600", color: "#999" },
  sub: { fontSize: 13, color: "#555", marginTop: 4 },
  subBug: { color: "#A32D2D" },
  hint: { fontSize: 12, color: "#999", marginTop: 3 },
  button: {
    marginTop: 10,
    backgroundColor: "#111",
    borderRadius: 8,
    paddingVertical: 9,
    alignItems: "center",
  },
  buttonBug: { backgroundColor: "#A32D2D" },
  buttonText: { color: "#fff", fontSize: 14, fontWeight: "700" },
});
