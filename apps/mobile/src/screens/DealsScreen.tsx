import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";

import { api } from "../api/client";
import type { Deal } from "../api/types";
import DealCard from "../components/DealCard";
import type { DealsStackParamList } from "../../App";

type Props = NativeStackScreenProps<DealsStackParamList, "DealsList">;

const FILTERS: { key: string | undefined; label: string }[] = [
  { key: undefined, label: "全部" },
  { key: "cheap", label: "便宜票" },
  { key: "error_fare", label: "BUG票" },
];

export default function DealsScreen({ navigation }: Props) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setError(null);
      setDeals(await api.deals(filter));
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filter]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  return (
    <View style={styles.container}>
      <View style={styles.filters}>
        {FILTERS.map((f) => (
          <Pressable key={f.label} onPress={() => setFilter(f.key)}>
            <Text style={[styles.filter, filter === f.key && styles.filterActive]}>{f.label}</Text>
          </Pressable>
        ))}
      </View>

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
  filters: { flexDirection: "row", gap: 8, padding: 12, backgroundColor: "#fff" },
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
  empty: { textAlign: "center", color: "#888", marginTop: 40 },
  error: { color: "#b3261e", textAlign: "center", margin: 24, lineHeight: 20 },
});
