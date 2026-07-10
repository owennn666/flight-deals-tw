import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
const PAGE_SIZE = 50;
const MAX_PRICE_DEBOUNCE_MS = 300;

export default function DealsScreen({ navigation }: Props) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const [routes, setRoutes] = useState<RouteInfo[]>([]);
  const [routeKey, setRouteKey] = useState<string>(ROUTE_ALL);
  const [minDiscount, setMinDiscount] = useState<number | undefined>(undefined);
  const [maxPriceInput, setMaxPriceInput] = useState<string>("");
  const [debouncedMaxPriceInput, setDebouncedMaxPriceInput] = useState<string>("");
  const [hideLcc, setHideLcc] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);

  // 分頁游標與進行中請求：用 ref 而非 state，避免分頁推進時把 load 的 identity 一起變動（見下方 fetchPage 依賴）
  const offsetRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    api.routes().then(setRoutes).catch(() => {});
  }, []);

  // 價格上限輸入 debounce 300ms 再生效，避免每個按鍵都打一次 API
  useEffect(() => {
    const t = setTimeout(() => setDebouncedMaxPriceInput(maxPriceInput), MAX_PRICE_DEBOUNCE_MS);
    return () => clearTimeout(t);
  }, [maxPriceInput]);

  const maxPrice = useMemo(() => {
    const n = Number(debouncedMaxPriceInput);
    return debouncedMaxPriceInput.trim() !== "" && Number.isFinite(n) && n > 0 ? n : undefined;
  }, [debouncedMaxPriceInput]);

  const selectedRoute = useMemo(
    () => routes.find((r) => `${r.origin}-${r.destination}` === routeKey),
    [routes, routeKey]
  );

  // 抓一頁資料；append=false 時取代既有列表（篩選變更/下拉重整），append=true 時接在後面（分頁載入）
  const fetchPage = useCallback(
    async (pageOffset: number, append: boolean) => {
      // 發新請求前中止前一個未完成的請求，防止舊請求慢回來蓋掉新結果（競態）
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      if (append) setLoadingMore(true);
      try {
        setError(null);
        const rows = await api.deals({
          type: filter,
          origin: selectedRoute?.origin,
          destination: selectedRoute?.destination,
          minDiscount,
          maxPrice,
          offset: pageOffset,
          limit: PAGE_SIZE,
          signal: controller.signal,
        });
        const filtered = hideLcc
          ? rows.filter((d) => !d.airline || !LCC_AIRLINES.includes(d.airline))
          : rows;
        setDeals((prev) => (append ? [...prev, ...filtered] : filtered));
        offsetRef.current = pageOffset + rows.length;
        setHasMore(rows.length === PAGE_SIZE);
      } catch (e) {
        if (e instanceof Error && e.name === "AbortError") return; // 被更新的請求取代，不算錯誤
        setError(e instanceof Error ? e.message : "載入失敗");
      } finally {
        setLoading(false);
        setRefreshing(false);
        setLoadingMore(false);
      }
    },
    [filter, selectedRoute, minDiscount, maxPrice, hideLcc]
  );

  // 篩選條件（含 debounce 後的價格上限）變更時：offset 歸零、清空舊資料重新載入
  useEffect(() => {
    offsetRef.current = 0;
    setHasMore(true);
    setLoading(true);
    fetchPage(0, false);
  }, [fetchPage]);

  const onRefresh = useCallback(() => {
    offsetRef.current = 0;
    setHasMore(true);
    setRefreshing(true);
    fetchPage(0, false);
  }, [fetchPage]);

  const onEndReached = useCallback(() => {
    if (loading || loadingMore || refreshing || !hasMore) return;
    fetchPage(offsetRef.current, true);
  }, [fetchPage, loading, loadingMore, refreshing, hasMore]);

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

  // 空清單文案：BUG 票分頁優先用專屬文案；其餘依「是否有生效的篩選」分兩種
  let emptyText: string;
  if (filter === "error_fare") {
    emptyText = "BUG 票（疑似標錯價）非常罕見，出現時會列在這裡並附風險提示。目前沒有進行中的 BUG 票。";
  } else if (activeChips.length > 0) {
    emptyText = "沒有符合篩選的好康，試著放寬條件";
  } else {
    emptyText = "目前沒有進行中的好康，資料每 15 分鐘更新";
  }

  return (
    <View style={styles.container}>
      <Text style={styles.subtitle}>跟這條航線平常的價格比，真的變便宜才列出</Text>
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
          onEndReached={onEndReached}
          onEndReachedThreshold={0.4}
          ListFooterComponent={loadingMore ? <ActivityIndicator style={{ marginVertical: 16 }} /> : null}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
          ListEmptyComponent={<Text style={styles.empty}>{emptyText}</Text>}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f2f3f5" },
  subtitle: { fontSize: 12, color: "#888", paddingHorizontal: 12, paddingTop: 10, backgroundColor: "#fff" },
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
