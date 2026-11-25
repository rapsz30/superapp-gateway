// Jalankan: node --test tests/proses.test.mjs   (Node 22.18+ membaca .ts langsung)
// Logika langkah proses AlurKerja yang dipindahkan dari StudentGateway (program/) ke matkul.
import assert from "node:assert/strict";
import { test } from "node:test";
import { MAKS_SKS_SEMESTER, evaluateRows, terapkanBatasSks } from "../src/lib/proses/recommend.ts";
import { hitungKeyakinan, nimCocok } from "../src/lib/proses/keyakinan.ts";
import { periksaTokenLayanan } from "../src/lib/proses/layanan.ts";
import { redactIdentity, toContract } from "../src/lib/proses/rencana.ts";

const mk = (sks) => ({ sks });

// ---------- batas SKS (dari program/tests/unit/batas-sks.test.ts, ditambah batas per prodi) ----------
test("batas bawaan 24 SKS memangkas mata kuliah baru dari belakang", () => {
  const r = terapkanBatasSks([mk(5), mk(4)], [mk(6), mk(6), mk(4)]);
  assert.equal(r.max, MAKS_SKS_SEMESTER);
  assert.equal(r.dipangkas, true);
  assert.deepEqual(r.baru, [mk(6), mk(6)]);
});

test("mata kuliah ulang tidak pernah dipangkas", () => {
  assert.deepEqual(terapkanBatasSks([mk(13), mk(13)], [mk(3)]).baru, []);
});

test("catatan dosen yang lebih kecil dipakai; yang lebih besar tidak melonggarkan panduan", () => {
  assert.equal(terapkanBatasSks([mk(4)], [mk(6), mk(6), mk(6)], 18).max, 18);
  assert.equal(terapkanBatasSks([], [mk(30)], 30).max, 24);
});

test("batas SKS mengikuti panduan prodi, bukan 24 yang tertanam", () => {
  const prodiLonggar = terapkanBatasSks([mk(4)], [mk(10), mk(10), mk(6)], undefined, 30);
  assert.equal(prodiLonggar.max, 30);
  assert.equal(prodiLonggar.dipangkas, false);
  const prodiKetat = terapkanBatasSks([mk(4)], [mk(6), mk(6), mk(6)], undefined, 18);
  assert.equal(prodiKetat.max, 18);
  assert.deepEqual(prodiKetat.baru, [mk(6), mk(6)]);
  // Catatan dosen tetap tidak boleh melampaui batas prodi.
  assert.equal(terapkanBatasSks([], [mk(30)], 28, 20).max, 20);
});

// ---------- keyakinan dan kecocokan NIM ----------
const khsLengkap = () => ({
  mahasiswa: { nama: "Alya Wijaya", nim: "20110001", prodi: "Informatika", sksKumulatif: 5, ipk: 3.5 },
  nilai: [
    { kode: "IF101", nama: "Algoritma", sks: 3, nilai: "A", semester: 1 },
    { kode: "IF102", nama: "Kalkulus", sks: 2, nilai: "B", semester: 1 },
  ],
});

test("KHS lengkap dan SKS cocok: keyakinan 1", () => {
  assert.equal(hitungKeyakinan(khsLengkap()), 1);
});

test("KHS tanpa baris nilai: keyakinan 0", () => {
  const k = khsLengkap();
  k.nilai = [];
  assert.equal(hitungKeyakinan(k), 0);
});

test("kolom kosong dan SKS tidak cocok menurunkan keyakinan di bawah ambang 0,9", () => {
  const k = khsLengkap();
  k.mahasiswa.nim = null;
  k.mahasiswa.sksKumulatif = 99;
  assert.ok(hitungKeyakinan(k) < 0.9);
});

test("NIM: sama lolos, beda ditolak, salah satu kosong tidak memblokir", () => {
  assert.equal(nimCocok("2011 0001", "20110001"), true);
  assert.equal(nimCocok("20110002", "20110001"), false);
  assert.equal(nimCocok(null, "20110001"), true);
  assert.equal(nimCocok("20110001", ""), true);
});

// ---------- privasi: nama dan NIM tidak boleh keluar ke AlurKerja ----------
test("redactIdentity membuang NIM dan nama (juga bagian nama) dari teks", () => {
  const khs = khsLengkap();
  const out = redactIdentity("NIM 20110001: Alya Wijaya perlu mengulang. Wijaya juga disarankan.", khs);
  assert.doesNotMatch(out, /20110001/);
  assert.doesNotMatch(out, /Alya|Wijaya/i);
  assert.match(out, /mahasiswa/);
});

test("toContract: bentuk kontrak, total SKS, peringatan dari data (bukan LLM), tanpa nama", () => {
  const khs = khsLengkap();
  khs.nilai.push({ kode: "IF103", nama: "Logika", sks: 2, nilai: "E", semester: 1 });
  const hasil = toContract(
    "rnc_1",
    {
      semester_target: 3,
      ringkasan: "Alya Wijaya sebaiknya mengulang Logika.",
      evaluasi_nilai: [],
      rekomendasi_semester_depan: [
        { kode: "IF103", nama: "Logika", sks: 2, alasan: "ulang", jenis: "ulang" },
        { kode: "IF301", nama: "Basis Data", sks: 3, alasan: "baru", jenis: "baru" },
      ],
    },
    khs,
  );
  assert.equal(hasil.rencana_ref, "rnc_1");
  assert.equal(hasil.total_sks, 5);
  assert.deepEqual(hasil.peringatan, ["IF103 belum lulus (nilai E), wajib diulang"]);
  assert.doesNotMatch(JSON.stringify(hasil), /Alya|Wijaya|20110001/i);
});

test("evaluateRows menandai E sebagai tidak lulus dan A sebagai lulus", () => {
  const k = khsLengkap();
  k.nilai.push({ kode: "IF103", nama: "Logika", sks: 2, nilai: "E", semester: 1 });
  const baris = Object.fromEntries(evaluateRows(k).map((r) => [r.kode, r.status_lulus]));
  assert.equal(baris.IF101, "Lulus");
  assert.equal(baris.IF103, "Tidak Lulus");
});

// ---------- token layanan ----------
const req = (auth) => new Request("http://x/api/matkul/recommend", { method: "POST", headers: auth ? { authorization: auth } : {} });

test("token layanan: tanpa konfigurasi 503, tanpa atau salah 401, benar lolos", () => {
  delete process.env.MATKUL_SERVICE_TOKEN;
  assert.equal(periksaTokenLayanan(req("Bearer apa-saja")).status, 503);
  process.env.MATKUL_SERVICE_TOKEN = "token-layanan-uji-1234567890";
  assert.equal(periksaTokenLayanan(req(null)).status, 401);
  assert.equal(periksaTokenLayanan(req("Bearer salah")).status, 401);
  assert.equal(periksaTokenLayanan(req("Basic token-layanan-uji-1234567890")).status, 401);
  assert.equal(periksaTokenLayanan(req("Bearer token-layanan-uji-1234567890")), null);
  assert.equal(periksaTokenLayanan(req("bearer token-layanan-uji-1234567890")), null);
});

test("token pengguna (JWT) tidak diterima sebagai token layanan", () => {
  process.env.MATKUL_SERVICE_TOKEN = "token-layanan-uji-1234567890";
  assert.equal(periksaTokenLayanan(req("Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc")).status, 401);
});
