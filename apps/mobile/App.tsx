import React, { useEffect } from "react";
import {
  NavigationContainer,
  createNavigationContainerRef,
  type NavigatorScreenParams,
} from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { StatusBar } from "expo-status-bar";
import * as Notifications from "expo-notifications";

import DealsScreen from "./src/screens/DealsScreen";
import DealDetailScreen from "./src/screens/DealDetailScreen";
import SubscriptionsScreen from "./src/screens/SubscriptionsScreen";
import SettingsScreen from "./src/screens/SettingsScreen";
import { registerForPushNotificationsAsync } from "./src/notifications/push";
import type { Deal } from "./src/api/types";

// 導覽型別（各畫面共用）
export type DealsStackParamList = {
  DealsList: undefined;
  DealDetail: { deal: Deal };
};

// 最外層 Tab 導覽的型別（給 navigationRef 用，涵蓋巢狀的 DealsStack）
export type RootTabParamList = {
  Deals: NavigatorScreenParams<DealsStackParamList>;
  Subscriptions: undefined;
  Settings: undefined;
};

// 讓「通知點擊」這種畫面外的事件也能導航
export const navigationRef = createNavigationContainerRef<RootTabParamList>();

const Stack = createNativeStackNavigator<DealsStackParamList>();
const Tab = createBottomTabNavigator();

function DealsStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="DealsList" component={DealsScreen} options={{ title: "便宜機票" }} />
      <Stack.Screen name="DealDetail" component={DealDetailScreen} options={{ title: "好康詳情" }} />
    </Stack.Navigator>
  );
}

// 推播的 data 欄位帶了整筆 deal → 點通知直接跳詳情，不必再打 API
function openDealFromNotification(data: unknown) {
  if (!data || typeof data !== "object" || !navigationRef.isReady()) return;
  navigationRef.navigate("Deals", { screen: "DealDetail", params: { deal: data as Deal } });
}

export default function App() {
  useEffect(() => {
    // 啟動：要通知權限並把 Expo push token 註冊到後端
    registerForPushNotificationsAsync().catch((e) => console.warn("push 註冊失敗", e));

    // App 由通知冷啟動時，開啟該筆好康
    Notifications.getLastNotificationResponseAsync().then((resp) => {
      if (resp) openDealFromNotification(resp.notification.request.content.data);
    });
    // App 執行中點通知
    const sub = Notifications.addNotificationResponseReceivedListener((resp) => {
      openDealFromNotification(resp.notification.request.content.data);
    });
    return () => sub.remove();
  }, []);

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar style="dark" />
      <Tab.Navigator screenOptions={{ headerShown: false }}>
        <Tab.Screen name="Deals" component={DealsStack} options={{ title: "好康" }} />
        <Tab.Screen name="Subscriptions" component={SubscriptionsScreen} options={{ title: "訂閱" }} />
        <Tab.Screen name="Settings" component={SettingsScreen} options={{ title: "設定" }} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
