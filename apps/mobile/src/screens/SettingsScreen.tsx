import React from "react";
import { ScrollView, StyleSheet, Text } from "react-native";

export default function SettingsScreen() {
  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.h}>設定</Text>
      {/* 推播開關先隱藏：後端目前沒有任何程式讀訂閱表送推播，這顆開關切了沒有實際效果，
          顯示出來等於做假承諾。等推播真的上線再打開。 */}

      <Text style={styles.section}>關於</Text>
      <Text style={styles.p}>
        本 App 為機票便宜票 / BUG 票（標錯價）/ 四腳票的資訊分享平台，僅提供資訊，不代訂機票。
        點擊訂票將導向第三方 OTA / 航司網站。
      </Text>

      <Text style={styles.section}>風險提醒</Text>
      <Text style={styles.p}>
        • BUG 票（疑似標錯價）不保證出票，請自行評估風險，建議先別訂不可退的旅館/行程。{"\n"}
        • 四腳票 / 隱藏城市票屬航司運送契約的灰色地帶（違約但通常不違法），可能導致後續航段被取消、
        里程被追討，使用前請自行了解風險。
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  h: { fontSize: 20, fontWeight: "800", color: "#111" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 16,
  },
  label: { fontSize: 16, color: "#222" },
  section: { fontSize: 15, fontWeight: "700", color: "#111", marginTop: 24 },
  p: { fontSize: 13, color: "#555", lineHeight: 20, marginTop: 8 },
});
