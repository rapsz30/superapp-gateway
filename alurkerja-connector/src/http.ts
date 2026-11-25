export class HttpError extends Error {
  constructor(public status: number, public body: unknown, message: string) {
    super(message);
  }
}

export async function postJson<T = any>(
  url: string,
  body: unknown,
  headers: Record<string, string> = {},
  timeoutMs = 120000
): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify(body ?? {}),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await res.text();
  let data: unknown = text;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* biarkan sebagai teks */
  }
  if (!res.ok) {
    const detail = typeof data === "object" && data && "error" in data ? String((data as any).error) : text.slice(0, 300);
    throw new HttpError(res.status, data, `POST ${url} -> ${res.status} ${detail}`);
  }
  return data as T;
}
