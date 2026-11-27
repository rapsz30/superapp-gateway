// Jalankan: node --test tests/proses.test.mjs   (Node 22.18+ membaca .ts langsung)
// Logika langkah proses AlurKerja yang dipindahkan dari StudentGateway (program/) ke matkul.
import assert from "node:assert/strict";
import { test } from "node:test";
import { MAKS_SKS_SEMESTER, evaluateRows, gabungKandidat, hanyaBatasSks, isiSampaiBatas, mataKuliahBaru, terapkanBatasSks } from "../src/lib/proses/recommend.ts";
import { hitungKeyakinan } from "../src/lib/proses/keyakinan.ts";
import { bacaTeksPdf } from "../src/lib/proses/pdf.ts";
import { bangunRingkasanAkademik } from "../src/lib/proses/ringkasan.ts";
import { bacaSekali } from "../src/lib/proses/bacaan.ts";
import { bandingkanNilai } from "../src/lib/proses/pratinjau.ts";
import { MAKS_KARAKTER, ringkasanDosen } from "../src/lib/proses/ringkasan-dosen.ts";
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

// ---------- revisi yang hanya membatasi SKS ----------
test("catatan yang hanya membatasi SKS dikenali", () => {
  for (const c of ["Maksimal 18 SKS.", "maks 18 sks saja ya", "Tolong ambil maksimum 21 SKS semester ini."]) {
    assert.equal(hanyaBatasSks(c), true, c);
  }
  for (const c of ["Maksimal 18 SKS, hapus IF303.", "Maksimal 18 SKS dan dahulukan Statistika", "Ganti Jaringan Komputer"]) {
    assert.equal(hanyaBatasSks(c), false, c);
  }
});

test("rencana sebelumnya diisi sampai batas, bukan dipangkas berlebihan", () => {
  const baru = (kode, sks) => ({ kode, sks, jenis: "baru" });
  const sebelumnya = {
    rekomendasi_semester_depan: [{ kode: "IF203", sks: 3, jenis: "ulang" },
      ...["IF301", "IF302", "IF303", "IF304", "IF305", "IF306"].map((k) => baru(k, 3)), baru("IF307", 2)],
  };
  const usulanLlm = [baru("IF301", 3), baru("IF302", 3)];
  const kandidat = gabungKandidat(mataKuliahBaru(sebelumnya), usulanLlm);
  assert.equal(kandidat.length, 7);
  const hasil = isiSampaiBatas([{ sks: 3 }], kandidat, 18);
  assert.deepEqual(hasil.map((x) => x.kode), ["IF301", "IF302", "IF303", "IF304", "IF305"]);
  // Sisa ruang diisi mata kuliah yang lebih kecil.
  assert.deepEqual(isiSampaiBatas([{ sks: 3 }], kandidat, 17).map((x) => x.kode), ["IF301", "IF302", "IF303", "IF304", "IF307"]);
});

// ---------- baca teks PDF ----------
test("baca PDF: coba ulang, lalu pakai pembaca cadangan", async () => {
  let n = 0;
  const sekaliGagal = async () => { if (++n === 1) throw new Error("bad XRef entry"); return " teks "; };
  assert.equal(await bacaTeksPdf(Buffer.from("x"), sekaliGagal, async () => "cadangan"), "teks");
  const rusak = async () => { throw new Error("bad XRef entry"); };
  assert.equal(await bacaTeksPdf(Buffer.from("x"), rusak, async () => "cadangan"), "cadangan");
  await assert.rejects(bacaTeksPdf(Buffer.from("x"), rusak, async () => { throw new Error("ENOENT"); }), /bad XRef/);
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

// ---------- ringkasan nilai untuk dasbor ----------
test("ringkasan akademik mengelompokkan per semester tanpa identitas", () => {
  const r = bangunRingkasanAkademik({
    mahasiswa: { nama: "Rahasia", nim: "123" },
    nilai: [
      { kode: "IF201", nama: "Struktur Data", sks: 4, nilai: "B", semester: 2 },
      { kode: "IF101", nama: "Algoritma", sks: 4, nilai: "A", semester: 1 },
      { kode: "IF203", nama: "Aljabar", sks: 3, nilai: "E", semester: 2 },
      { kode: "UM101", nama: "Bahasa", sks: 2, nilai: "D", semester: "" },
    ],
  });
  assert.equal(r.sks_total, 13);
  assert.equal(r.sks_lulus, 10);
  assert.equal(r.jumlah_mk, 4);
  assert.deepEqual(r.per_semester.map((s) => s.semester), [1, 2, 0]);
  assert.equal(r.per_semester[0].ip, 4);
  assert.deepEqual(r.perhatian.map((m) => [m.kode, m.status]), [["IF203", "tidak_lulus"], ["UM101", "bersyarat"]]);
  assert.deepEqual(r.distribusi.map((d) => d.nilai), ["A", "B", "D", "E"]);
  assert.doesNotMatch(JSON.stringify(r), /Rahasia|123/);
});

// ---------- KHS dibaca satu kali ----------
const gudangMemori = () => {
  const isi = new Map();
  return { isi, ambil: async (s) => isi.get(s) ?? null, simpan: async (s, h) => (isi.has(s) ? isi.get(s) : (isi.set(s, h), h)) };
};

test("berkas yang sama dibaca sekali; berkas berbeda dibaca baru", async () => {
  const gudang = gudangMemori();
  let kali = 0;
  const baca = async () => ({ nilai: [{ kode: `IF${++kali}` }] });
  const a = await bacaSekali(Buffer.from("khs-a"), baca, gudang);
  const lagi = await bacaSekali(Buffer.from("khs-a"), baca, gudang);
  const b = await bacaSekali(Buffer.from("khs-b"), baca, gudang);
  assert.deepEqual(lagi, a);
  assert.notDeepEqual(b, a);
  assert.equal(kali, 2);
});

test("hasil kosong tidak disimpan dan galat penyimpanan tidak menggagalkan pembacaan", async () => {
  const gudang = gudangMemori();
  await bacaSekali(Buffer.from("x"), async () => ({ nilai: [] }), gudang);
  assert.equal(gudang.isi.size, 0);
  const rusak = { ambil: async () => { throw new Error("db"); }, simpan: async () => { throw new Error("db"); } };
  const h = await bacaSekali(Buffer.from("x"), async () => ({ nilai: [{ kode: "IF1" }] }), rusak);
  assert.equal(h.nilai[0].kode, "IF1");
});

// ---------- nilai yang diubah mahasiswa di wizard ----------
test("nilai tanpa perubahan tidak menghasilkan catatan", () => {
  const asli = [{ kode: "IF101", nama: "Algoritma", sks: 4, nilai: "A" }, { kode: "X", nama: "Y", sks: null, nilai: "T" }];
  assert.deepEqual(bandingkanNilai(asli, [{ kode: "X", nama: "Y", sks: 0, nilai: "" }, { kode: "if101", nama: "Algoritma", sks: 4, nilai: "a" }]), []);
});

test("nilai diubah, ditambah, dan dihapus dicatat", () => {
  const c = bandingkanNilai(
    [{ kode: "IF203", nama: "Aljabar", sks: 3, nilai: "E" }, { kode: "UM101", nama: "Bahasa", sks: 2, nilai: "B" }],
    [{ kode: "IF203", nama: "Aljabar", sks: 3, nilai: "C" }, { kode: "IF999", nama: "Baru", sks: 3, nilai: "A" }],
  );
  assert.equal(c.length, 3);
  assert.match(c[0], /IF203 diubah mahasiswa menjadi 3 SKS, nilai C \(di KHS: 3 SKS, nilai E\)/);
  assert.match(c[1], /IF999 ditambahkan/);
  assert.match(c[2], /UM101 dihapus/);
});

// ---------- rangkuman untuk form dosen ----------
test("rangkuman dosen memuat angka dan mata kuliah, aman dari HTML, dan dibatasi panjangnya", () => {
  const khs = { mahasiswa: { ipk: 3 }, nilai: [{ kode: "IF101", nama: "A", sks: 4, nilai: "A" }] };
  const rencana = { rencana_mk: [{ kode: "IF301", nama: "<b>PBO</b>", sks: 3 }], total_sks: 3, alasan: "ok", peringatan: ["cek"] };
  const h = ringkasanDosen(rencana, khs, { ke: 1, catatan: "Maksimal 18 SKS" });
  assert.match(h, /IPK 3,00 · SKS lulus 4 · Rencana 3 SKS \(1 mata kuliah\)/);
  assert.match(h, /Revisi ke-1/);
  assert.match(h, /&lt;b&gt;PBO/);
  const panjang = ringkasanDosen({ ...rencana, alasan: "x".repeat(9000) }, khs);
  assert.ok(panjang.length <= MAKS_KARAKTER + 100);
  assert.match(panjang, /dipotong/);
});
