import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import type { Deal } from "../api/types";

const BADGE: Record<string, { label: string; color: string }> = {
  cheap: { label: "💰 便宜票", color: "#0a7d2c" },
  error_fare: { label: "🐞 疑似BUG票", color: "#b3261e" },
  nested: { label: "🧩 構票", color: "#5b4b8a" },
};

export default function DealCard({ deal, onPress }: { deal: Deal; onPress: () => void }) {
  const badge = BADGE[deal.type] ?? { label: "✈️ 好康", color: "#333" };
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={styles.row}>
        <Text style={[styles.badge, { color: badge.color }]}>{badge.label}</Text>
        <Text style={styles.route}>{deal.route_str}</Text>
      </View>
      <Text style={styles.price}>
        {deal.price.toLocaleString()} {deal.currency}
        <Text style={styles.off}>　省 {Math.round(deal.discount_pct * 100)}%</Text>
      </Text>
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
