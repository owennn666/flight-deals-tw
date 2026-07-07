import React, { useEffect, useState } from "react";
import {
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { api } from "../api/client";
import type { RouteInfo } from "../api/types";
import { getDeviceId } from "../notifications/push";

export default function SubscriptionsScreen() {
  const [routes, setRoutes] = useState<RouteInfo[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [maxPrice, setMaxPrice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.routes().then(setRoutes).catch(() => setRoutes([]));
    api
      .getSubscription(getDeviceId())
      .then((s) => {
        setSelected(new Set(s.routes ?? []));
        if (s.max_price) setMaxPrice(String(s.max_price));
      })
      .catch(() => {});
  }, []);

  const toggle = (label: string) => {
    const next = new Set(selected);
    if (next.has(label)) next.delete(label);
    else next.add(label);
    setSelected(next);
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.setSubscription({
        device: getDeviceId(),
        routes: Array.from(selected),
        max_price: maxPrice ? Number(maxPrice) : null,
        cabin: null,
      });
      Alert.alert("已儲存", "之後符合條件的好康會推播給你。");
    } catch (e) {
      Alert.alert("儲存失敗", e instanceof Error ? e.message : "");
    } finally {
      setSaving(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ padding: 16 }}>
      <Text style={styles.h}>追蹤航線</Text>
      <Text style={styles.hint}>選你想收到好康推播的航線</Text>
      <View style={styles.chips}>
        {routes.map((r) => {
          const key = `${r.origin}->${r.destination}`;
          const active = selected.has(key);
          return (
            <Pressable key={key} onPress={() => toggle(key)}>
              <Text style={[styles.chip, active && styles.chipActive]}>{r.label}</Text>
            </Pressable>
          );
        })}
        {routes.length === 0 ? <Text style={styles.hint}>（讀不到航線，確認後端已啟動）</Text> : null}
      </View>

      <Text style={styles.h}>預算上限（TWD）</Text>
      <TextInput
        style={styles.input}
        keyboardType="number-pad"
        placeholder="例：8000（留白表示不限）"
        value={maxPrice}
        onChangeText={setMaxPrice}
      />

      <Pressable style={[styles.button, saving && { opacity: 0.6 }]} onPress={save} disabled={saving}>
        <Text style={styles.buttonText}>{saving ? "儲存中…" : "儲存訂閱"}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  h: { fontSize: 16, fontWeight: "700", color: "#111", marginTop: 12 },
  hint: { fontSize: 13, color: "#888", marginTop: 4, marginBottom: 8 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 },
  chip: {
    fontSize: 14,
    color: "#333",
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 18,
    backgroundColor: "#eef0f2",
    overflow: "hidden",
  },
  chipActive: { color: "#fff", backgroundColor: "#0a7d2c" },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 10,
    padding: 12,
    fontSize: 16,
    marginTop: 8,
  },
  button: {
    backgroundColor: "#111",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 24,
  },
  buttonText: { color: "#fff", fontSize: 16, fontWeight: "700" },
});
