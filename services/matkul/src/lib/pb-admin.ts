import PocketBase from "pocketbase";

export function pbAdmin() {
  const url =
    process.env.NEXT_PUBLIC_PB_URL ||
    process.env.POCKETBASE_URL ||
    "http://127.0.0.1:8090";
  return new PocketBase(url);
}

export async function ensureAdminAuth(pb: PocketBase) {
  const email = process.env.PB_ADMIN_EMAIL;
  const password = process.env.PB_ADMIN_PASSWORD;

  if (!email || !password) {
    throw new Error("PB_ADMIN_EMAIL / PB_ADMIN_PASSWORD belum diset di .env.local");
  }

  if (!pb.authStore.isValid) {
    await pb.admins.authWithPassword(email, password);
  }
}
