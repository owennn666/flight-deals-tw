import React from "react";
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import type { DealsStackParamList } from "../../App";

type Props = NativeStackScreenProps<DealsStackParamList, "DealDetail">;

export default function DealDetailScreen({ route }: Props) {
  const { deal } = route.params;
  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.route}>{deal.route_str}</Text>
      <Text style={styles.price}>
        {deal.price.toLocaleString()} {deal.currency}
      </Text>
      <Text style={styles.sub}>
        基準 {Math.round(deal.baseline_median).toLocaleString()} · 省{" "}
        {Math.round(deal.discount_pct * 100)}% · {deal.tier}
      </Text>
      {deal.depart_date ? <Text style={styles.sub}>出發：{deal.depart_date}</Text> : null}

      <View style={styles.reasons}>
        {deal.reasons.map((r, i) => (
          <Text key={i} style={styles.reason}>
            • {r}
          </Text>
        ))}
      </View>

      {deal.needs_verification ? (
        <View style={styles.warn}>
          <Text style={styles.warnText}>
            ⚠️ 疑似標錯價（BUG 票）：航司不保證出票，訂票風險自負，建議先別訂不可退的旅館/行程。
          </Text>
        </View>
      ) : null}

      {deal.deep_link ? (
        <Pressable style={styles.button} onPress={() => Linking.openURL(deal.deep_link as string)}>
          <Text style={styles.buttonText}>前往訂票（外部網站）</Text>
        </Pressable>
      ) : null}

      <Text style={styles.disclaimer}>
        本平台僅提供資訊分享，不代訂機票。點擊訂票將前往第三方 OTA / 航司網站，實際票價與供應以該網站為準。
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  route: { fontSize: 22, fontWeight: "800", color: "#111" },
  price: { fontSize: 32, fontWeight: "900", color: "#111", marginTop: 8 },
  sub: { fontSize: 14, color: "#555", marginTop: 4 },
  reasons: { marginTop: 16 },
  reason: { fontSize: 14, color: "#333", marginVertical: 2 },
  warn: { backgroundColor: "#fdecea", borderRadius: 10, padding: 12, marginTop: 16 },
  warnText: { color: "#8c1d18", fontSize: 13, lineHeight: 19 },
  button: {
    backgroundColor: "#111",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 20,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  disclaimer: { fontSize: 11, color: "#999", marginTop: 16, lineHeight: 16 },
});
