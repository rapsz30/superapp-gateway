export type Config = {
  /** Alamat AlurKerja; REST Camunda 7 ada di {baseUrl}/engine-rest. */
  baseUrl: string;
  externalTaskBaseUrl: string;
  etFetchPath: string;
  /** Akun Basic Auth Camunda untuk External Task (jalur /engine-rest menjawab 401 Basic). */
  etUsername: string;
  etPassword: string;
  /** Hanya tugas dari proses ini yang diambil (processDefinitionKey). */
  processName: string;
  /** Awalan nama topik, supaya beberapa worker (mis. StudentGateway lama) tidak berebut tugas yang sama. */
  topicPrefix: string;
  workerId: string;
  lockMs: number;
  pollMs: number;
  /** Alamat layanan matkul (jaringan internal), tempat endpoint /api/matkul/*. */
  gatewayUrl: string;
  /** Token layanan matkul (MATKUL_SERVICE_TOKEN). */
  gatewayToken: string;
  llmProvider: string;
  llmModel: string;
};

const trimSlash = (s: string) => s.replace(/\/+$/, "");

export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const baseUrl = trimSlash(env.ALURKERJA_BASE_URL ?? "");
  return {
    baseUrl,
    externalTaskBaseUrl: trimSlash(env.ALURKERJA_EXTERNAL_TASK_BASE_URL || (baseUrl ? `${baseUrl}/engine-rest` : "")),
    etFetchPath: env.ALURKERJA_ET_FETCH_PATH || "/external-task/fetchAndLock",
    etUsername: env.ALURKERJA_ET_USERNAME ?? "",
    etPassword: env.ALURKERJA_ET_PASSWORD ?? "",
    processName: env.ALURKERJA_PROCESS_NAME ?? "",
    topicPrefix: env.TOPIC_PREFIX ?? "",
    workerId: env.WORKER_ID || "superapp-worker-1",
    lockMs: Number(env.WORKER_LOCK_MS) || 120000,
    pollMs: Number(env.WORKER_POLL_MS) || 3000,
    gatewayUrl: trimSlash(env.GATEWAY_URL ?? ""),
    gatewayToken: env.GATEWAY_TOKEN ?? "",
    llmProvider: env.LLM_PROVIDER ?? "openai",
    llmModel: env.LLM_MODEL ?? "",
  };
}

/** Pastikan konfigurasi wajib terisi sebelum worker berjalan. */
export function assertWorkerConfig(c: Config) {
  const missing: string[] = [];
  if (!c.externalTaskBaseUrl) missing.push("ALURKERJA_BASE_URL / ALURKERJA_EXTERNAL_TASK_BASE_URL");
  if (!(c.etUsername && c.etPassword)) missing.push("ALURKERJA_ET_USERNAME + ALURKERJA_ET_PASSWORD (Basic Auth Camunda)");
  if (!c.gatewayUrl) missing.push("GATEWAY_URL");
  if (!c.gatewayToken) missing.push("GATEWAY_TOKEN (sama dengan MATKUL_SERVICE_TOKEN)");
  if (!c.processName) missing.push("ALURKERJA_PROCESS_NAME (kunci proses; mencegah mengambil tugas proses lain)");
  if (missing.length) throw new Error(`Konfigurasi belum lengkap: ${missing.join(", ")}`);
}
