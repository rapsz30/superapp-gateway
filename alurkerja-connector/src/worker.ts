import type { Config } from "./config.js";
import { completeTask, failTask, fetchAndLock, type ExternalTask } from "./externalTask.js";
import { gatewayClient } from "./gateway.js";

/** Nama topik dasar. Nama di BPMN = TOPIC_PREFIX + nama dasar (mis. "superapp-ekstraksi-khs"). */
export const BASE_TOPICS = {
  ekstraksi: "ekstraksi-khs",
  rekomendasi: "rekomendasi-matkul",
  revisi: "revisi-rencana",
} as const;

export type TopicMap = Record<keyof typeof BASE_TOPICS, string>;

export const topicsFor = (prefix = ""): TopicMap => ({
  ekstraksi: prefix + BASE_TOPICS.ekstraksi,
  rekomendasi: prefix + BASE_TOPICS.rekomendasi,
  revisi: prefix + BASE_TOPICS.revisi,
});

type Gateway = ReturnType<typeof gatewayClient>;
type Handler = (vars: Record<string, any>, gw: Gateway) => Promise<Record<string, unknown>>;

const need = (vars: Record<string, any>, key: string) => {
  if (vars[key] === undefined || vars[key] === null || vars[key] === "") throw new Error(`variabel proses "${key}" tidak ada`);
  return vars[key];
};
const optNum = (v: unknown) => (v === undefined || v === null || v === "" ? undefined : Number(v));

/**
 * Alamat email mahasiswa untuk notifikasi hasil. Chatbot sebaiknya mengirimnya sebagai variabel `email_mahasiswa`
 * saat proses dimulai. Bila tidak ada, dipakai alamat demo fiktif agar langkah kirim email tidak menggagalkan
 * penyelesaian tugas dosen (Studio tidak mengevaluasi ekspresi bersyarat pada penerima email).
 */
export const DEMO_EMAIL = process.env.DEMO_STUDENT_EMAIL || "mahasiswa.demo@example.com";

export const handlers: Record<string, Handler> = {
  [BASE_TOPICS.ekstraksi]: async (vars, gw) => {
    const r = await gw.extractKhs(String(need(vars, "khs_file_id")), optNum(vars.semester_target), String(need(vars, "id_pengajuan")));
    return {
      khs_ref: r.khs_ref, ipk: r.ipk, sks_lulus: r.sks_lulus, mk_lulus: r.mk_lulus, mk_ulang: r.mk_ulang, keyakinan: r.keyakinan, prodi: r.prodi ?? null,
      nim_cocok: r.nim_cocok ?? true,
      ...(vars.email_mahasiswa ? {} : { email_mahasiswa: DEMO_EMAIL }),
    };
  },

  [BASE_TOPICS.rekomendasi]: async (vars, gw) => {
    const r = await gw.recommend(String(need(vars, "khs_ref")), optNum(vars.semester_target));
    return {
      rencana_ref: r.rencana_ref,
      rencana_mk: r.rencana_mk,
      total_sks: r.total_sks,
      alasan: r.alasan,
      peringatan: r.peringatan,
      ringkasan_dosen: r.ringkasan_dosen ?? "",
      ada_peringatan: r.peringatan.length > 0,
      jumlah_revisi: 0,
    };
  },

  [BASE_TOPICS.revisi]: async (vars, gw) => {
    const r = await gw.revise(String(need(vars, "rencana_ref")), String(need(vars, "catatan_dosen")));
    return {
      rencana_ref: r.rencana_ref,
      rencana_mk: r.rencana_mk,
      total_sks: r.total_sks,
      alasan: r.alasan,
      peringatan: r.peringatan,
      ringkasan_dosen: r.ringkasan_dosen ?? "",
      ada_peringatan: r.peringatan.length > 0,
      jumlah_revisi: (Number(vars.jumlah_revisi) || 0) + 1,
    };
  },
};

/** Kerjakan satu tugas, catat durasi (untuk angka pengukuran), lalu complete/fail. */
export async function processTask(c: Config, task: ExternalTask, gw: Gateway = gatewayClient(c)) {
  const started = Date.now();
  // Nama topik di BPMN berawalan TOPIC_PREFIX; handler dikunci dengan nama dasar.
  const dasar = c.topicPrefix && task.topicName.startsWith(c.topicPrefix) ? task.topicName.slice(c.topicPrefix.length) : task.topicName;
  const handler = handlers[dasar];
  try {
    if (!handler) throw new Error(`topic tidak dikenal: ${task.topicName}`);
    const out = await handler(task.variables, gw);
    await completeTask(c, task.id, out);
    log("ok", task, Date.now() - started);
    return true;
  } catch (e: any) {
    log("gagal", task, Date.now() - started, e?.message);
    // retries null = belum pernah gagal. Sambungan putus dan jawaban LLM yang rusak biasanya hilang saat diulang.
    const sisa = Math.max(0, (task.retries ?? c.maxAttempts) - 1);
    try {
      await failTask(c, task.id, String(e?.message ?? e), sisa);
    } catch (e2: any) {
      console.error(`[worker] fail() juga gagal untuk ${task.id}: ${e2?.message}`);
    }
    return false;
  }
}

function log(status: string, t: ExternalTask, ms: number, err?: string) {
  // Tanpa isi variabel, agar tidak mencetak data mahasiswa.
  console.log(
    JSON.stringify({ at: new Date().toISOString(), topic: t.topicName, task: t.id, instance: t.processInstanceId, status, ms, ...(err ? { err } : {}) })
  );
}

/** Satu putaran polling; mengembalikan jumlah tugas yang diambil. */
export async function pollOnce(c: Config, gw: Gateway = gatewayClient(c)) {
  const tasks = await fetchAndLock(c, Object.values(topicsFor(c.topicPrefix)));
  for (const t of tasks) await processTask(c, t, gw);
  return tasks.length;
}

export async function runWorker(c: Config, signal?: AbortSignal) {
  const gw = gatewayClient(c);
  console.log(`[worker] mulai: ${c.workerId}, topik: ${Object.values(topicsFor(c.topicPrefix)).join(", ")}, llm: ${c.llmProvider}/${c.llmModel}`);
  while (!signal?.aborted) {
    let n = 0;
    try {
      n = await pollOnce(c, gw);
    } catch (e: any) {
      console.error(`[worker] polling gagal: ${e?.message}`);
    }
    if (n === 0) await new Promise((r) => setTimeout(r, c.pollMs));
  }
}
