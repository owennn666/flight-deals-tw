import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { api } from "../api/client";

// 收到通知時前景也顯示
Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

// 裝置識別：優先用 Expo push token；拿不到（模擬器）就用隨機 id。
// 註：scaffold 版存在記憶體，重開 App 會變；正式版請用 expo-secure-store 持久化。
let cachedDeviceId: string | null = null;

export function getDeviceId(): string {
  if (!cachedDeviceId) {
    cachedDeviceId = "dev-" + Math.random().toString(36).slice(2, 10);
  }
  return cachedDeviceId;
}

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  const existing = await Notifications.getPermissionsAsync();
  let status = existing.status;
  if (status !== "granted") {
    status = (await Notifications.requestPermissionsAsync()).status;
  }
  if (status !== "granted") {
    return null; // 使用者拒絕，仍可用 App，只是收不到 push
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "default",
      importance: Notifications.AndroidImportance.HIGH,
    });
  }

  const projectId =
    (Constants.expoConfig?.extra as Record<string, unknown> | undefined)?.eas &&
    ((Constants.expoConfig?.extra as { eas?: { projectId?: string } }).eas?.projectId);

  const tokenResp = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : undefined
  );
  const token = tokenResp.data;
  cachedDeviceId = token;

  try {
    await api.registerDevice(token, Platform.OS);
  } catch (e) {
    console.warn("註冊裝置到後端失敗（後端沒開？）", e);
  }
  return token;
}
