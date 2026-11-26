// Pemilah teks balasan AI menjadi paragraf dan daftar. Model diminta menulis teks biasa, tetapi sesekali tetap
// mengirim markdown ringan atau daftar bernomor dalam satu baris. Hasilnya data biasa, bukan HTML.

export type BlokTeks =
  | { jenis: 'paragraf'; isi: string }
  | { jenis: 'judul'; isi: string }
  | { jenis: 'nomor'; mulai: number; butir: string[] }
  | { jenis: 'butir'; butir: string[] }

/** "Langkahnya: 1. Satu. 2. Dua." menjadi satu butir per baris. Hanya bila nomornya berurutan dari 1. */
function pisahDaftarSebaris(baris: string): string[] {
  const posisi: number[] = []
  let dari = 0
  for (let n = 1; ; n++) {
    const cocok = new RegExp(`(?:^|\\s)(${n}[.)])\\s`).exec(baris.slice(dari))
    if (!cocok) break
    const letak = dari + cocok.index + cocok[0].indexOf(cocok[1])
    posisi.push(letak)
    dari = letak + cocok[1].length
  }
  if (posisi.length < 2) return [baris]
  return [0, ...posisi].map((awal, i, semua) => baris.slice(awal, semua[i + 1])).map((s) => s.trim()).filter(Boolean)
}

export function pilahTeks(teks: string): BlokTeks[] {
  const blok: BlokTeks[] = []
  const baris = teks.replace(/\r\n?/g, '\n').split('\n').flatMap(pisahDaftarSebaris)
  for (const mentah of baris) {
    const s = mentah.trim()
    // Baris kosong dan garis pemisah tabel atau markdown tidak ditampilkan.
    if (!s || /^[|\s:*_-]{3,}$/.test(s)) continue
    const nomor = /^(\d{1,2})[.)]\s+(.*)$/.exec(s)
    const butir = /^(?:[-•–]|\*(?!\*))\s+(.*)$/.exec(s)
    const judul = /^#{1,6}\s+(.*)$/.exec(s)
    const akhir = blok[blok.length - 1]
    if (nomor) {
      if (akhir?.jenis === 'nomor') akhir.butir.push(nomor[2])
      else blok.push({ jenis: 'nomor', mulai: Number(nomor[1]), butir: [nomor[2]] })
    } else if (butir) {
      if (akhir?.jenis === 'butir') akhir.butir.push(butir[1])
      else blok.push({ jenis: 'butir', butir: [butir[1]] })
    } else if (judul) {
      blok.push({ jenis: 'judul', isi: judul[1] })
    } else if (/^\|.*\|$/.test(s)) {
      blok.push({ jenis: 'paragraf', isi: s.split('|').map((x) => x.trim()).filter(Boolean).join(' · ') })
    } else {
      blok.push({ jenis: 'paragraf', isi: s })
    }
  }
  return blok
}

/** Potongan sebaris: **tebal** dan `kode`. Bagian berindeks ganjil adalah yang bertanda. */
export function pilahSebaris(teks: string): { isi: string; gaya: 'biasa' | 'tebal' | 'kode' }[] {
  return teks.split(/(\*\*[^*]+\*\*|`[^`]+`)/).filter(Boolean).map((s) => {
    if (s.length > 4 && s.startsWith('**') && s.endsWith('**')) return { isi: s.slice(2, -2), gaya: 'tebal' }
    if (s.length > 2 && s.startsWith('`') && s.endsWith('`')) return { isi: s.slice(1, -1), gaya: 'kode' }
    return { isi: s, gaya: 'biasa' }
  })
}
