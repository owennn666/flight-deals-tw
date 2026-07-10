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

// 裝置識別：與 push token 脫鉤（token 拿不到、使用者拒絕通知權限，一樣要能回穩定 id）。
// Web：用 localStorage 持久化的 UUID，重新整理不會變。
// 原生：目前仍存記憶體（重開 App 會變；正式版請用 expo-secure-store 持久化）。
const DEVICE_ID_KEY = "fd_device_id";
let cachedDeviceId: string | null = null;

function generateUuidV4(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // 沒有 crypto.randomUUID（舊瀏覽器 / RN 環境）→ 手工湊一個 v4 格式的 id
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function hasLocalStorage(): boolean {
  return Platform.OS === "web" && typeof localStorage !== "undefined";
}

export function getOrCreateDeviceId(): string {
  if (hasLocalStorage()) {
    try {
      const stored = localStorage.getItem(DEVICE_ID_KEY);
      if (stored) return stored;
      const created = generateUuidV4();
      localStorage.setItem(DEVICE_ID_KEY, created);
      return created;
    } catch {
      // localStorage 不可用（例如無痕模式擋存取）→ 退化為記憶體 id
    }
  }
  if (!cachedDeviceId) {
    cachedDeviceId = "dev-" + generateUuidV4();
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

  const eas = Constants.expoConfig?.extra?.eas as { projectId?: string } | undefined;
  const projectId = eas?.projectId;

  const tokenResp = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : undefined
  );
  const token = tokenResp.data;

  try {
    await api.registerDevice(token, Platform.OS, getOrCreateDeviceId());
  } catch (e) {
    console.warn("註冊裝置到後端失敗（後端沒開？）", e);
  }
  return token;
}
