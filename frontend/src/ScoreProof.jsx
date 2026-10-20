import { useEffect, useState } from 'react'
import { api } from './api'
import { Card } from './ui'

const pct = (x) => `${Math.round(x * 100)}%`
const NAMES = { graphlas: 'Graphlas', newest_document: 'Always the newest document', most_linked_document: 'The most linked document', random_pick: 'A random document' }
const BAND = { green: 'bg-ok', yellow: 'bg-warn', red: 'bg-bad' }

/* Why the 0-100 score deserves trust: measured against a hidden truth in the simulated data. */
export default function ScoreProof({ compact = false }) {
  const [v, setV] = useState(null)
  useEffect(() => { api.validation().then(setV).catch(() => {}) }, [])
  if (!v) return null
  return (
    <Card className="space-y-4">
      <div>
        <h3 className="font-semibold">Why can you trust the score?</h3>
        <p className="text-sm text-muted">We checked it against a hidden truth: does a document really state the current value? The model never scores a document it trained on.</p>
      </div>
      <div className="space-y-1.5">
        <p className="text-sm font-medium">How often is the top answer a correct document? ({v.groups} questions that mix correct and outdated documents)</p>
        {Object.entries(v.top_answer_correct).map(([k, x]) => (
          <div key={k} className="flex items-center gap-2 text-sm">
            <span className="w-52 shrink-0">{NAMES[k]}</span>
            <div className="h-3 flex-1 overflow-hidden rounded bg-line"><div className={k === 'graphlas' ? 'h-full bg-[linear-gradient(100deg,#F0343C,#B3308F_60%,#7B2FBE)]' : 'h-full bg-muted/60'} style={{ width: pct(x) }} /></div>
            <span className="w-10 text-right font-semibold tabular-nums">{pct(x)}</span>
          </div>
        ))}
      </div>
      <div className="space-y-1.5">
        <p className="text-sm font-medium">What do the colours mean? Share of documents that really state the current value</p>
        {v.bands.map((b) => (
          <div key={b.band} className="flex items-center gap-2 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${BAND[b.band]}`} />
            <span className="w-28 shrink-0">{b.band === 'green' ? 'Green' : b.band === 'yellow' ? 'Yellow' : 'Red'} ({b.range})</span>
            <div className="h-3 flex-1 overflow-hidden rounded bg-line"><div className={`h-full ${BAND[b.band]}`} style={{ width: pct(b.state_the_current_value ?? 0) }} /></div>
            <span className="w-10 text-right font-semibold tabular-nums">{b.state_the_current_value == null ? '-' : pct(b.state_the_current_value)}</span>
          </div>
        ))}
      </div>
      {!compact && <p className="text-xs text-muted">Overall separation of correct from outdated documents (AUC): {v.auc_vs_truth}. {v.note}</p>}
    </Card>
  )
}
