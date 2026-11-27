// Jalankan: node --test tests/   (Node 22.18+ membaca .ts langsung)
import assert from "node:assert/strict";
import { test } from "node:test";
import { peringatanKonteks, prodiCocok } from "../src/lib/konteks.ts";

const konteks = (nama = "Informatika") => ({
  mahasiswa: { id: "1", nama_lengkap: "A", nim: "20110001" },
  prodi: { id: "p", kode: "IF-S1", nama, jenjang: "S1", jurusan: null, fakultas: null },
  pembimbing_akademik: null,
  panduan: { id: "g", versi: 2, judul: "x", berlaku_mulai: null, teks_karakter: 10 },
});

test("nama prodi dibandingkan longgar", () => {
  assert.equal(prodiCocok("Informatika", "Informatika"), true);
  assert.equal(prodiCocok("Program Studi Informatika - Program Sarjana", "Informatika"), true);
  assert.equal(prodiCocok("INFORMATIKA (S1)", "Informatika"), true);
  assert.equal(prodiCocok("Teknik Industri", "Informatika"), false);
  assert.equal(prodiCocok("", "Informatika"), true); // tidak bisa dibandingkan, tidak diperingatkan
  assert.equal(prodiCocok(null, "Informatika"), true);
});

test("peringatan hanya muncul saat prodi KHS beda", () => {
  assert.deepEqual(peringatanKonteks({ mahasiswa: { prodi: "Informatika" } }, konteks()), []);
  const w = peringatanKonteks({ mahasiswa: { prodi: "Teknik Industri" } }, konteks());
  assert.equal(w.length, 1);
  assert.match(w[0], /Teknik Industri/);
  assert.match(w[0], /panduan prodi akun/);
});

test("peringatan dilewati untuk prodi terbuka / panduan pribadi", () => {
  const k = konteks("Dummy Umum");
  k.prodi.terbuka = true;
  assert.deepEqual(peringatanKonteks({ mahasiswa: { prodi: "Teknik Industri" } }, k), []);
  const k2 = konteks("Dummy Umum");
  k2.panduan.pribadi = true;
  assert.deepEqual(peringatanKonteks({ mahasiswa: { prodi: "Teknik Industri" } }, k2), []);
});

