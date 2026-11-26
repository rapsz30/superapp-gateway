import { pilahSebaris, pilahTeks } from '@/src/lib/teks-ai'

function Sebaris({ teks }: { teks: string }) {
  return <>{pilahSebaris(teks).map((p, i) => p.gaya === 'tebal' ? <strong key={i}>{p.isi}</strong> : p.gaya === 'kode' ? <code key={i}>{p.isi}</code> : <span key={i}>{p.isi}</span>)}</>
}

/** Tampilkan teks AI sebagai paragraf dan daftar. Tanpa HTML mentah. */
export function TeksAI({ teks }: { teks: string }) {
  return <div className="teks-ai">{pilahTeks(teks).map((b, i) => {
    if (b.jenis === 'nomor') return <ol key={i} start={b.mulai}>{b.butir.map((x, n) => <li key={n}><Sebaris teks={x} /></li>)}</ol>
    if (b.jenis === 'butir') return <ul key={i}>{b.butir.map((x, n) => <li key={n}><Sebaris teks={x} /></li>)}</ul>
    return <p key={i}>{b.jenis === 'judul' ? <strong><Sebaris teks={b.isi} /></strong> : <Sebaris teks={b.isi} />}</p>
  })}</div>
}
