import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import type { AddressInfo } from "node:net";
import { loadConfig } from "../src/config.js";
import { pollOnce } from "../src/worker.js";

type Call = { method: string; url: string; auth?: string; body: any };

/** Server tiruan: AlurKerja (external task + client API) dan layanan mata kuliah. */
async function startMock(queue: any[]) {
  const calls: Call[] = [];
  const server = http.createServer((req, res) => {
    let raw = "";
    req.on("data", (d) => (raw += d));
    req.on("end", () => {
      const body = (() => {
        try {
          return raw ? JSON.parse(raw) : {};
        } catch {
          return {}; // mis. form-urlencoded dari endpoint token
        }
      })();
      calls.push({ method: req.method!, url: req.url!, auth: req.headers.authorization, body });
      const json = (code: number, o: unknown) => {
        res.writeHead(code, { "content-type": "application/json" });
        res.end(JSON.stringify(o));
      };
      const u = req.url!;
      if (u === "/api/v1/integration/auth_token/slug1/login") {
        if (body.client_id !== "cid" || body.client_secret !== "sec") return json(401, { error: "invalid credentials" });
        return json(200, { data: { access_token: "tok2", expires_in: 300 }, message: "Success" });
      }
      if (u.startsWith("/api/v1/tasklist/my-task"))
        return json(200, { data: { content: [{ id: 85, name: "Unggah KHS", task_definition_key: "Task_Unggah", process_instance_id: "pi-1" }] } });
      if (u.startsWith("/api/v1/tasklist/process-instance/pi-1"))
        return json(200, { data: { state: "ACTIVE", started_at: "2026-11-23T11:40:39Z", ended_at: null } });
      if (u === "/sso/token") {
        const form = new URLSearchParams(raw);
        if (form.get("grant_type") !== "client_credentials" || form.get("client_id") !== "cid" || form.get("client_secret") !== "sec")
          return json(401, { error: "unauthorized_client" });
        return json(200, { access_token: "abc", expires_in: 300 });
      }
      if (u === "/external-task/fetchAndLock") return json(200, queue.splice(0));
      if (u.endsWith("/complete") || u.endsWith("/fail")) return json(200, {});
      if (u === "/api/matkul/extract-khs")
        return json(200, { khs_ref: "khs_1", ipk: 3.1, sks_lulus: 96, mk_lulus: ["IF101"], mk_ulang: ["IF210"], keyakinan: 0.94, prodi: "Informatika - Program Sarjana" });
      if (u === "/api/matkul/recommend")
        return json(200, { rencana_ref: "rnc_1", rencana_mk: [{ kode: "IF320", nama: "ML", sks: 3, alasan: "x" }], total_sks: 3, alasan: "ok", peringatan: ["IF210 belum lulus"] });
      if (u === "/api/matkul/revise")
        return json(200, { rencana_ref: "rnc_2", rencana_mk: [], total_sks: 0, alasan: "rev", peringatan: [] });
      if (u === "/api/matkul/gagal") return json(500, { error: "boom" });
      if (u.startsWith("/api/v1/tasklist/ps/direct-start"))
        return json(200, { data: { process_instance_id: "pi-1" } });
      if (u.startsWith("/api/v1/tasklist/ps/tasks/t1/direct-complete"))
        return json(200, { data: { hasNextUserTask: true, nextTask: { taskId: "t2" } } });
      json(404, { error: "tidak ada" });
    });
  });
  await new Promise<void>((r) => server.listen(0, r));
  const base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  return { base, calls, close: () => server.close() };
}

const cfgFor = (base: string) =>
  loadConfig({
    ALURKERJA_BASE_URL: base,
    ALURKERJA_EXTERNAL_TASK_BASE_URL: base,
    ALURKERJA_ET_USERNAME: "akun",
    ALURKERJA_ET_PASSWORD: "rahasia",
    ALURKERJA_PROCESS_NAME: "ps",
    GATEWAY_URL: base,
    GATEWAY_TOKEN: "token-layanan",
  } as any);

const BASIC = `Basic ${Buffer.from("akun:rahasia").toString("base64")}`;

const task = (id: string, topicName: string, vars: Record<string, unknown>) => ({
  id,
  topicName,
  processInstanceId: "pi-1",
  variables: Object.fromEntries(Object.entries(vars).map(([k, v]) => [k, { type: "String", value: v, valueInfo: {} }])),
});

test("tiga topik: ambil tugas, panggil layanan, complete dengan variabel yang benar", async () => {
  const m = await startMock([
    task("a", "ekstraksi-khs", { khs_file_id: "file_1", semester_target: 7, id_pengajuan: "pgj_1" }),
    task("b", "rekomendasi-matkul", { khs_ref: "khs_1", semester_target: 7 }),
    task("c", "revisi-rencana", { rencana_ref: "rnc_1", catatan_dosen: "maks 18 SKS", jumlah_revisi: 1 }),
  ]);
  try {
    assert.equal(await pollOnce(cfgFor(m.base)), 3);

    const done = (id: string) => m.calls.find((c) => c.url === `/external-task/${id}/complete`)!;
    assert.equal(done("a").auth, BASIC);
    // format Camunda: workerId + variabel bertipe; array/objek menjadi String berisi JSON
    assert.equal(done("a").body.workerId, "superapp-worker-1");
    assert.deepEqual(done("a").body.variables, {
      khs_ref: { value: "khs_1", type: "String" },
      ipk: { value: 3.1, type: "Double" },
      sks_lulus: { value: 96, type: "Integer" },
      mk_lulus: { value: '["IF101"]', type: "String" },
      mk_ulang: { value: '["IF210"]', type: "String" },
      keyakinan: { value: 0.94, type: "Double" },
      prodi: { value: "Informatika - Program Sarjana", type: "String" },
      nim_cocok: { value: true, type: "Boolean" },
      email_mahasiswa: { value: "mahasiswa.demo@example.com", type: "String" }, // cadangan demo bila chatbot tidak mengirimnya
    });
    assert.deepEqual(done("b").body.variables.ada_peringatan, { value: true, type: "Boolean" });
    assert.deepEqual(done("b").body.variables.jumlah_revisi, { value: 0, type: "Integer" });
    assert.deepEqual(done("c").body.variables.jumlah_revisi, { value: 2, type: "Integer" });
    assert.deepEqual(done("c").body.variables.ada_peringatan, { value: false, type: "Boolean" });

    // nilai variabel di-unwrap sebelum dikirim ke layanan
    const ext = m.calls.find((c) => c.url === "/api/matkul/extract-khs")!;
    assert.deepEqual(ext.body, { khs_file_id: "file_1", semester_target: 7, id_pengajuan: "pgj_1" });
  } finally {
    m.close();
  }
});

test("topik tak dikenal atau variabel hilang berujung fail, bukan crash", async () => {
  const m = await startMock([task("x", "topik-aneh", {}), task("y", "rekomendasi-matkul", {})]);
  try {
    assert.equal(await pollOnce(cfgFor(m.base)), 2);
    const fails = m.calls.filter((c) => c.url.endsWith("/fail"));
    assert.equal(fails.length, 2);
    assert.equal(fails[0].body.workerId, "superapp-worker-1");
    assert.equal(fails[0].body.retries, 0);
    assert.match(fails[0].body.errorMessage, /topic tidak dikenal/);
    assert.match(fails[1].body.errorMessage, /khs_ref/);
    assert.equal(m.calls.filter((c) => c.url.endsWith("/complete")).length, 0);
  } finally {
    m.close();
  }
});

test("External Task memakai Basic Auth akun Camunda; layanan matkul memakai token layanan", async () => {
  const m = await startMock([task("z", "ekstraksi-khs", { khs_file_id: "f1", semester_target: 5, id_pengajuan: "pgj_1" })]);
  try {
    assert.equal(await pollOnce(cfgFor(m.base)), 1);
    const et = m.calls.filter((c) => c.url.startsWith("/external-task"));
    assert.ok(et.length === 2 && et.every((c) => c.auth === BASIC));
    const layanan = m.calls.filter((c) => c.url.startsWith("/api/matkul"));
    assert.ok(layanan.length === 1 && layanan[0].auth === "Bearer token-layanan");
  } finally {
    m.close();
  }
});

test("assertWorkerConfig: kredensial, token layanan, dan kunci proses wajib", async () => {
  const { assertWorkerConfig } = await import("../src/config.js");
  assert.throws(() => assertWorkerConfig(loadConfig({} as any)), /ALURKERJA_BASE_URL/);
  const hampir = loadConfig({ ALURKERJA_BASE_URL: "http://a", ALURKERJA_ET_USERNAME: "u", ALURKERJA_ET_PASSWORD: "p", GATEWAY_URL: "http://m" } as any);
  assert.throws(() => assertWorkerConfig(hampir), /GATEWAY_TOKEN[\s\S]*ALURKERJA_PROCESS_NAME/);
  assert.doesNotThrow(() => assertWorkerConfig({ ...hampir, gatewayToken: "t", processName: "kunci" }));
});

test("email_mahasiswa dari chatbot dipertahankan; bila kosong diisi alamat demo", async () => {
  const m = await startMock([task("p", "ekstraksi-khs", { khs_file_id: "f", semester_target: 5, id_pengajuan: "pgj_1", email_mahasiswa: "budi@contoh.test" })]);
  try {
    assert.equal(await pollOnce(cfgFor(m.base)), 1);
    const sel = m.calls.find((c) => c.url === "/external-task/p/complete")!;
    assert.equal(sel.body.variables.email_mahasiswa, undefined); // tidak ditimpa
  } finally {
    m.close();
  }
});


test("TOPIC_PREFIX: hanya topik berawalan yang diambil, dan fetchAndLock dibatasi pada proses ini", async () => {
  const m = await startMock([
    task("a", "superapp-ekstraksi-khs", { khs_file_id: "f", semester_target: 5, id_pengajuan: "pgj_9" }),
    task("b", "superapp-rekomendasi-matkul", { khs_ref: "khs_1" }),
  ]);
  try {
    const cfg = { ...cfgFor(m.base), topicPrefix: "superapp-", processName: "perencanaan-studi-superapp" };
    assert.equal(await pollOnce(cfg), 2);

    const fetch = m.calls.find((c) => c.url === "/external-task/fetchAndLock")!;
    assert.deepEqual(
      fetch.body.topics.map((t: any) => [t.topicName, t.processDefinitionKey]),
      [
        ["superapp-ekstraksi-khs", "perencanaan-studi-superapp"],
        ["superapp-rekomendasi-matkul", "perencanaan-studi-superapp"],
        ["superapp-revisi-rencana", "perencanaan-studi-superapp"],
      ],
    );
    assert.equal(m.calls.filter((c) => c.url.endsWith("/complete")).length, 2);
    assert.equal(m.calls.find((c) => c.url === "/api/matkul/extract-khs")!.body.id_pengajuan, "pgj_9");
  } finally {
    m.close();
  }
});

test("tanpa id_pengajuan langkah ekstraksi gagal dengan pesan jelas (bukan memanggil layanan)", async () => {
  const m = await startMock([task("a", "ekstraksi-khs", { khs_file_id: "f", semester_target: 5 })]);
  try {
    assert.equal(await pollOnce(cfgFor(m.base)), 1);
    const gagal = m.calls.find((c) => c.url === "/external-task/a/fail")!;
    assert.match(gagal.body.errorMessage, /id_pengajuan/);
    assert.equal(m.calls.some((c) => c.url === "/api/matkul/extract-khs"), false);
  } finally {
    m.close();
  }
});

test("nim_cocok=false dari layanan diteruskan sebagai variabel proses", async () => {
  const m = await startMock([task("a", "ekstraksi-khs", { khs_file_id: "f", semester_target: 5, id_pengajuan: "pgj_1" })]);
  // ganti jawaban mock: layanan melaporkan NIM tidak cocok
  const asli = m.close;
  try {
    const { handlers } = await import("../src/worker.js");
    const hasil = await handlers["ekstraksi-khs"](
      { khs_file_id: "f", id_pengajuan: "pgj_1", email_mahasiswa: "a@b.c" },
      { extractKhs: async () => ({ khs_ref: "k", ipk: null, sks_lulus: 0, mk_lulus: [], mk_ulang: [], keyakinan: 0, nim_cocok: false }) } as any,
    );
    assert.equal(hasil.nim_cocok, false);
    assert.equal(hasil.keyakinan, 0);
  } finally {
    asli();
  }
});
