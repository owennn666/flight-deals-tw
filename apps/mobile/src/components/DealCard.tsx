import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Deal } from "../api/types";
import { AIRLINE_NAMES } from "../api/client";

const BADGE: Record<string, { label: string; color: string }> = {
  cheap: { label: "💰 便宜票", color: "#0a7d2c" },
  error_fare: { label: "🐞 疑似BUG票", color: "#b3261e" },
  nested: { label: "🧩 構票", color: "#5b4b8a" },
};

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
  const badge = BADGE[deal.type] ?? { label: "✈️ 好康", color: "#333" };
  const flightInfo = flightInfoLine(deal);
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.row}>
        <Text style={[styles.badge, { color: badge.color }]}>{badge.label}</Text>
        <Text style={styles.route}>{deal.route_str}</Text>
      </View>
      <Text style={styles.price}>
        {deal.price.toLocaleString()} {deal.currency}
        <Text style={styles.off}>　比平常低 {Math.round(deal.discount_pct * 100)}%</Text>
      </Text>
      {flightInfo ? <Text style={styles.sub}>{flightInfo}</Text> : null}
      <Text style={styles.sub}>
        基準 {Math.round(deal.baseline_median).toLocaleString()} · {deal.tier}
        {deal.needs_verification ? " · ⚠️需複核" : ""}
      </Text>
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
    shadowColor: "#000",
    shadowOpacity: 0.06,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  badge: { fontSize: 13, fontWeight: "600" },
  route: { fontSize: 15, fontWeight: "700", color: "#111" },
  price: { fontSize: 20, fontWeight: "800", color: "#111", marginTop: 6 },
  off: { fontSize: 14, fontWeight: "700", color: "#0a7d2c" },
  sub: { fontSize: 12, color: "#666", marginTop: 4 },
});
