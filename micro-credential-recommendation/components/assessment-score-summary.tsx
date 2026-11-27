import { ClipboardList, Flag } from 'lucide-react'

const MAX_SCORE = 1000
const THRESHOLD = 665

const segments = [
  { key: 'theory', name: 'Teori', value: 100 },
  { key: 'essay', name: 'Esai', value: 231.3 },
  { key: 'profile', name: 'Profil', value: 120 },
] as const

const formatScore = (value: number) =>
  value.toLocaleString('id-ID', { minimumFractionDigits: 0, maximumFractionDigits: 1 })

const GAUGE = { cx: 120, cy: 118, r: 100, stroke: 20, gap: 5 }
// Rounded caps extend half the stroke beyond each path end, so ends are inset and gaps widened to keep caps from touching.
const CAP_ANGLE = GAUGE.stroke / 2 / GAUGE.r
const GAP_ANGLE = (GAUGE.stroke + GAUGE.gap) / GAUGE.r

function pointAt(angle: number) {
  return { x: GAUGE.cx - GAUGE.r * Math.cos(angle), y: GAUGE.cy - GAUGE.r * Math.sin(angle) }
}

function arcPath(start: number, end: number) {
  const from = pointAt(start)
  const to = pointAt(end)
  return `M ${from.x.toFixed(2)} ${from.y.toFixed(2)} A ${GAUGE.r} ${GAUGE.r} 0 0 1 ${to.x.toFixed(2)} ${to.y.toFixed(2)}`
}

function ScoreGauge({ total }: { total: number }) {
  const parts = [...segments.map(({ key, value }) => ({ key, value })), { key: 'rest', value: Math.max(0, MAX_SCORE - total) }]
    .filter((part) => part.value > 0)
  const available = Math.PI - 2 * CAP_ANGLE - (parts.length - 1) * GAP_ANGLE
  let cursor = CAP_ANGLE
  const arcs = parts.map((part) => {
    const start = cursor
    const end = start + (part.value / MAX_SCORE) * available
    cursor = end + GAP_ANGLE
    return { ...part, d: arcPath(start, end) }
  })

  return <svg className="score-gauge-svg" viewBox="0 0 240 132" role="img" aria-label={`Skor keseluruhan ${formatScore(total)} dari 1.000 poin`}>
    {arcs.map((arc) => <path key={arc.key} d={arc.d} className={`score-gauge-segment ${arc.key}`} />)}
  </svg>
}

export function AssessmentScoreSummary() {
  const total = segments.reduce((sum, segment) => sum + segment.value, 0)
  const gap = Math.max(0, THRESHOLD - total)

  return <article className="score-summary-card">
    <div className="score-summary-gauge">
      <h3 className="score-summary-heading"><span aria-hidden="true"><ClipboardList /></span>Skor keseluruhan</h3>
      <div className="score-gauge">
        <ScoreGauge total={total} />
        <div className="score-gauge-center">
          <strong>{formatScore(total)}</strong>
          <span>/ 1.000 poin</span>
        </div>
        <div className="score-gauge-scale" aria-hidden="true"><span>0</span><span>1.000</span></div>
      </div>
      <ul className="score-gauge-legend">
        {segments.map((segment) => <li key={segment.key}>
          <i className={segment.key} aria-hidden="true" />
          <span>{segment.name}<span className="sr-only">: {formatScore(segment.value)} poin</span></span>
        </li>)}
            </ul>
    </div>

    <div className="score-summary-threshold">
      <h3 className="score-summary-heading"><span aria-hidden="true"><Flag /></span>Batas minimum kesiapan</h3>
      <p className="score-threshold-value">{THRESHOLD} poin</p>
      <p className="score-threshold-note">Dari total 1.000 poin</p>
      <dl className="score-threshold-stats">
        <div><dt>Skor Anda</dt><dd>{formatScore(total)} poin</dd></div>
        <div><dt>Selisih menuju ambang minimum</dt><dd>{formatScore(gap)} poin</dd></div>
      </dl>
    </div>
  </article>
}
