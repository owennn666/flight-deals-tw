import Constants from "expo-constants";

const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, string | undefined>;

/**
 * Supabase 連線資訊（前端直接讀 Supabase 的自動 API）。
 * 部署（Vercel）用環境變數：
 *   EXPO_PUBLIC_SUPABASE_URL       例：https://xxxx.supabase.co
 *   EXPO_PUBLIC_SUPABASE_ANON_KEY  Supabase 的 anon public key
 * 本機開發也可放 apps/mobile/.env（同名 EXPO_PUBLIC_* 變數）或 app.json 的 extra。
 */
export const SUPABASE_URL: string =
  (process.env.EXPO_PUBLIC_SUPABASE_URL as string | undefined) ?? extra.supabaseUrl ?? "";

export const SUPABASE_ANON_KEY: string =
  (process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY as string | undefined) ?? extra.supabaseAnonKey ?? "";
