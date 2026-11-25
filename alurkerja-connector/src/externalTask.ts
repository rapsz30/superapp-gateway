import type { Config } from "./config.js";
import { postJson } from "./http.js";

export type ExternalTask = {
  id: string;
  topicName: string;
  processInstanceId?: string;
  retries?: number | null;
  /** Variabel sudah di-unwrap menjadi nilai biasa. */
  variables: Record<string, any>;
};

/**
 * External Task memakai REST API Camunda 7 (`/engine-rest`). Instalasi on-premise menjawab 401 dengan
 * `WWW-Authenticate: Basic` di jalur itu, jadi autentikasinya Basic (akun Camunda).
 */
const authHeaders = async (c: Config): Promise<Record<string, string>> => ({
  authorization: `Basic ${Buffer.from(`${c.etUsername}:${c.etPassword}`).toString("base64")}`,
});

/** Camunda mengirim variabel sebagai {type, value, valueInfo}; ambil value-nya. */
export function unwrapVariables(raw: Record<string, any> | undefined): Record<string, any> {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(raw ?? {})) {
    out[k] = v && typeof v === "object" && "value" in v ? v.value : v;
  }
  return out;
}

/**
 * Camunda mewajibkan variabel bertipe saat complete/fail. Angka bulat -> Integer, pecahan -> Double,
 * array/objek -> String berisi JSON (tipe "Json" butuh plugin Spin yang belum tentu terpasang).
 */
export function toCamundaVariables(vars: Record<string, unknown>): Record<string, { value: unknown; type: string }> {
  const out: Record<string, { value: unknown; type: string }> = {};
  for (const [k, v] of Object.entries(vars)) {
    if (v === null || v === undefined) out[k] = { value: null, type: "Null" };
    else if (typeof v === "boolean") out[k] = { value: v, type: "Boolean" };
    else if (typeof v === "number") out[k] = Number.isInteger(v) ? { value: v, type: "Integer" } : { value: v, type: "Double" };
    else if (typeof v === "string") out[k] = { value: v, type: "String" };
    else out[k] = { value: JSON.stringify(v), type: "String" };
  }
  return out;
}

/** Fetch-and-lock, format Camunda 7: { workerId, maxTasks, topics: [{ topicName, lockDuration }] }. */
export async function fetchAndLock(c: Config, topics: string[], maxTasks = 5): Promise<ExternalTask[]> {
  const data = await postJson<any>(
    `${c.externalTaskBaseUrl}${c.etFetchPath}`,
    {
      workerId: c.workerId,
      maxTasks,
      topics: topics.map((topicName) => ({
        topicName,
        lockDuration: c.lockMs,
        // Hanya proses ini: topik yang sama di proses lain tidak diambil.
        ...(c.processName ? { processDefinitionKey: c.processName } : {}),
      })),
    },
    await authHeaders(c)
  );
  const list: any[] = Array.isArray(data) ? data : Array.isArray(data?.data) ? data.data : [];
  return list.map((t) => ({
    id: String(t.id),
    topicName: String(t.topicName),
    processInstanceId: t.processInstanceId,
    retries: t.retries ?? null,
    variables: unwrapVariables(t.variables),
  }));
}

/** Complete: { workerId, variables: { nama: { value, type } } }. */
export async function completeTask(c: Config, id: string, variables: Record<string, unknown>) {
  return postJson(
    `${c.externalTaskBaseUrl}/external-task/${encodeURIComponent(id)}/complete`,
    { workerId: c.workerId, variables: toCamundaVariables(variables) },
    await authHeaders(c)
  );
}

/** Fail: { workerId, errorMessage, errorDetails, retries, retryTimeout }. retries 0 membuat incident yang terlihat di Camunda. */
export async function failTask(c: Config, id: string, errorMessage: string, _variables: Record<string, unknown> = {}) {
  return postJson(
    `${c.externalTaskBaseUrl}/external-task/${encodeURIComponent(id)}/fail`,
    { workerId: c.workerId, errorMessage: errorMessage.slice(0, 500), errorDetails: errorMessage, retries: 0, retryTimeout: 0 },
    await authHeaders(c)
  );
}
