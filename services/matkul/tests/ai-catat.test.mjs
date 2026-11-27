import assert from "node:assert/strict";
import { test } from "node:test";
import { catatPemakaianAi, denganPemilik } from "../src/lib/ai-catat.ts";

test("gagal mengirim catatan tidak melempar dan tidak menunggu identity", async () => {
  const tokenLama = process.env.AI_CATAT_TOKEN;
  const fetchLama = globalThis.fetch;
  process.env.AI_CATAT_TOKEN = "test-token";
  let body;
  globalThis.fetch = async (_url, init) => {
    body = JSON.parse(init.body);
    throw new Error("identity tidak tersedia");
  };
  try {
    assert.doesNotThrow(() => denganPemilik({ akunId: "akun-uji" }, () => catatPemakaianAi("baca_khs", {
      layanan: "matkul", model: "test", token_masuk: 0, token_keluar: 0, durasi_ms: 1, berhasil: false,
    })));
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(body.akun_id, "akun-uji");
  } finally {
    globalThis.fetch = fetchLama;
    if (tokenLama === undefined) delete process.env.AI_CATAT_TOKEN;
    else process.env.AI_CATAT_TOKEN = tokenLama;
  }
});
