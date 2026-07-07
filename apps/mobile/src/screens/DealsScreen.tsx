import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { api, LCC_AIRLINES } from "../api/client";
import type { Deal, RouteInfo } from "../api/types";
import DealCard from "../components/DealCard";
import type { DealsStackParamList } from "../../App";

type Props = NativeStackScreenProps<DealsStackParamList, "DealsList">;

const FILTERS: { key: string | undefined; label: string }[] = [
  { key: undefined, label: "全部" },
  { key: "cheap", label: "便宜票" },
  { key: "error_fare", label: "BUG票" },
];

const DISCOUNT_OPTIONS: { key: number | undefined; label: string }[] = [
  { key: undefined, label: "不限" },
  { key: 0.25, label: "≥25%" },
  { key: 0.4, label: "≥40%" },
];

// 航線清單固定放在 client.ts 的 ROUTES；這裡透過 api.routes() 讀（同一份資料）
const ROUTE_ALL = "__all__";

export default function DealsScreen({ navigation }: Props) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const [routes, setRoutes] = useState<RouteInfo[]>([]);
  const [routeKey, setRouteKey] = useState<string>(ROUTE_ALL);
  const [minDiscount, setMinDiscount] = useState<number | undefined>(undefined);
  const [maxPriceInput, setMaxPriceInput] = useState<string>("");
  const [hideLcc, setHideLcc] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  useEffect(() => {
    api.routes().then(setRoutes).catch(() => {});
  }, []);

  const maxPrice = useMemo(() => {
    const n = Number(maxPriceInput);
    return maxPriceInput.trim() !== "" && !Number.isNaN(n) && n > 0 ? n : undefined;
  }, [maxPriceInput]);

  const selectedRoute = useMemo(
    () => routes.find((r) => `${r.origin}-${r.destination}` === routeKey),
    [routes, routeKey]
  );

  const load = useCallback(async () => {
    try {
      setError(null);
      const rows = await api.deals({
        type: filter,
        origin: selectedRoute?.origin,
        destination: selectedRoute?.destination,
        minDiscount,
        maxPrice,
      });
      setDeals(hideLcc ? rows.filter((d) => !d.airline || !LCC_AIRLINES.includes(d.airline)) : rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter, selectedRoute, minDiscount, maxPrice, hideLcc]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const activeChips: { label: string; onClear: () => void }[] = [];
  if (selectedRoute) activeChips.push({ label: selectedRoute.label, onClear: () => setRouteKey(ROUTE_ALL) });
  if (minDiscount !== undefined) {
    activeChips.push({
      label: `折扣≥${Math.round(minDiscount * 100)}%`,
      onClear: () => setMinDiscount(undefined),
    });
  }
  if (maxPrice !== undefined) {
    activeChips.push({ label: `價格≤${maxPrice.toLocaleString()}`, onClear: () => setMaxPriceInput("") });
  }
  if (hideLcc) activeChips.push({ label: "已隱藏廉航", onClear: () => setHideLcc(false) });

  return (
    <View style={styles.container}>
      <View style={styles.filters}>
        {FILTERS.map((f) => (
          <Pressable key={f.label} onPress={() => setFilter(f.key)}>
            <Text style={[styles.filter, filter === f.key && styles.filterActive]}>{f.label}</Text>
          </Pressable>
        ))}
        <Pressable onPress={() => setPanelOpen((v) => !v)}>
          <Text style={[styles.filter, panelOpen && styles.filterActive]}>篩選 {panelOpen ? "▲" : "▼"}</Text>
        </Pressable>
      </View>

      {panelOpen ? (
        <View style={styles.panel}>
          <Text style={styles.panelLabel}>航線</Text>
          <View style={styles.chipsRow}>
            <Pressable onPress={() => setRouteKey(ROUTE_ALL)}>
              <Text style={[styles.chip, routeKey === ROUTE_ALL && styles.chipActive]}>不限</Text>
            </Pressable>
            {routes.map((r) => {
              const key = `${r.origin}-${r.destination}`;
              return (
                <Pressable key={key} onPress={() => setRouteKey(key)}>
                  <Text style={[styles.chip, routeKey === key && styles.chipActive]}>{r.label}</Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={styles.panelLabel}>最低折扣</Text>
          <View style={styles.chipsRow}>
            {DISCOUNT_OPTIONS.map((opt) => (
              <Pressable key={opt.label} onPress={() => setMinDiscount(opt.key)}>
                <Text style={[styles.chip, minDiscount === opt.key && styles.chipActive]}>{opt.label}</Text>
              </Pressable>
            ))}
          </View>

          <Text style={styles.panelLabel}>價格上限</Text>
          <TextInput
            style={styles.input}
            value={maxPriceInput}
            onChangeText={setMaxPriceInput}
            placeholder="不限（例如 15000）"
            keyboardType="numeric"
          />

          <View style={styles.switchRow}>
            <Text style={styles.panelLabel}>隱藏廉航</Text>
            <Switch value={hideLcc} onValueChange={setHideLcc} />
          </View>
        </View>
      ) : null}

      {activeChips.length > 0 ? (
        <View style={styles.activeRow}>
          {activeChips.map((c) => (
            <Pressable key={c.label} onPress={c.onClear} style={styles.activeChip}>
              <Text style={styles.activeChipText}>{c.label} ✕</Text>
            </Pressable>
          ))}
        </View>
      ) : null}

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} />
      ) : error ? (
        <Text style={styles.error}>
          {error}
          {"\n\n"}確認 Supabase 設定正確（EXPO_PUBLIC_SUPABASE_URL / ANON_KEY），且 GitHub Actions 已跑過至少一次抓票。
        </Text>
      ) : (
        <FlatList
          data={deals}
          keyExtractor={(d) => String(d.id)}
          renderItem={({ item }) => (
            <DealCard deal={item} onPress={() => navigation.navigate("DealDetail", { deal: item })} />
          )}
          contentContainerStyle={{ paddingVertical: 8 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load();
              }}
            />
          }
          ListEmptyComponent={<Text style={styles.empty}>目前沒有好康，下拉刷新看看。</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f2f3f5" },
  filters: { flexDirection: "row", gap: 8, padding: 12, backgroundColor: "#fff", flexWrap: "wrap" },
  filter: {
    fontSize: 14,
    color: "#555",
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 16,
    backgroundColor: "#eef0f2",
    overflow: "hidden",
  },
  filterActive: { color: "#fff", backgroundColor: "#111" },
  panel: { backgroundColor: "#fff", paddingHorizontal: 12, paddingBottom: 12, gap: 4 },
  panelLabel: { fontSize: 12, color: "#888", marginTop: 8, marginBottom: 4 },
  chipsRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    fontSize: 13,
    color: "#555",
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: 14,
    backgroundColor: "#eef0f2",
    overflow: "hidden",
  },
  chipActive: { color: "#fff", backgroundColor: "#111" },
  input: {
    borderWidth: 1,
    borderColor: "#ddd",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    color: "#111",
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: 8,
  },
  activeRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, paddingHorizontal: 12, paddingTop: 10 },
  activeChip: {
    backgroundColor: "#e6e9ff",
    borderRadius: 14,
    paddingVertical: 5,
    paddingHorizontal: 10,
  },
  activeChipText: { fontSize: 12, color: "#2b3aa8", fontWeight: "600" },
  empty: { textAlign: "center", color: "#888", marginTop: 40 },
  error: { color: "#b3261e", textAlign: "center", margin: 24, lineHeight: 20 },
});
