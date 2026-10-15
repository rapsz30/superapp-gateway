export function getSessionKey() {
  if (typeof window === "undefined") return "";
  let key = sessionStorage.getItem("session_key");
  if (!key) {
    key = crypto.randomUUID();
    sessionStorage.setItem("session_key", key);
  }
  return key;
}
