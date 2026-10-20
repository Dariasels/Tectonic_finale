import { useEffect, useState } from 'react'
import { api, errText } from '../api'
import { useUser } from '../user'
import ScoreProof from '../ScoreProof'
import { Button, Card, ErrorBox } from '../ui'

export default function Model() {
  const { user } = useUser()
  const [status, setStatus] = useState(null)
  const [scale, setScale] = useState(null)
  const [msg, setMsg] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => { api.modelStatus(user.person_id).then(setStatus); api.scale().then(setScale) }
  useEffect(load, [user?.person_id])

  const retrain = async () => {
    setBusy(true); setError('')
    try { const r = await api.retrain(user.person_id); setMsg(`Retrained in ${r.seconds} s. Accuracy (AUC) ${r.auc_before} to ${r.auc_after}. ${r.scores_changed_over_5_points} scores moved by more than 5 points.`); load() }
    catch (e) { setError(errText(e)) } finally { setBusy(false) }
  }
  const toggle = async () => {
    try { await api.setPolicy({ user_id: user.person_id, auto: !status.auto }); load() } catch (e) { setError(errText(e)) }
  }
  const reset = async () => { await api.reset(); setMsg('Rebuilding 84k graph edges and retraining XGBoost... ready in about 15 seconds.') }

  if (!status || !scale) return <p className="p-6 text-sm text-muted">Loading...</p>
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card className="space-y-3">
        <h2 className="text-[26px] font-extrabold">Automatic retraining</h2>
        <div>
          <div className="mb-1 flex justify-between text-sm"><span>{status.new_since_train} of {status.threshold} new or changed documents</span><span>{status.days_since} of {status.max_days} days</span></div>
          <div className="h-3 overflow-hidden rounded bg-line"><div className="h-full bg-gradient-to-r from-orange to-magenta" style={{ width: `${status.progress * 100}%` }} /></div>
        </div>
        <p className="text-sm text-muted">{status.rule}</p>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={status.auto} disabled={!status.can_retrain} onChange={toggle} />Retrain automatically</label>
          <Button onClick={retrain} disabled={busy || !status.can_retrain}>{busy ? 'Training...' : 'Retrain now'}</Button>
        </div>
        {!status.can_retrain && <p className="text-sm text-muted">Only {status.who_can_retrain.toLowerCase()} Switch to one of them to try it.</p>}
        {msg && <p className="text-sm text-oktext">{msg}</p>}
        <ErrorBox>{error}</ErrorBox>
        <p className="text-sm text-muted">Model accuracy on simulated data (AUC): {status.model_auc_cv}. It shows the pipeline works, not real-world accuracy. Trained on {status.n_labels?.toLocaleString()} labels.</p>
      </Card>
      <div className="lg:col-span-2"><ScoreProof /></div>
      <Card className="space-y-2">
        <h2 className="text-[26px] font-extrabold">Scale</h2>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          {[['People', scale.people], ['Teams', scale.teams], ['Countries', scale.countries], ['Documents', scale.documents], ['Graph edges', scale.edges], ['Sources', scale.sources.length]].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-soft p-2"><dt className="text-xs text-muted">{k}</dt><dd className="text-lg font-semibold tabular-nums">{v.toLocaleString()}</dd></div>
          ))}
        </dl>
        <p className="text-sm text-muted">Full rebuild: <b>{scale.full_rebuild_seconds} s</b>. New document: <b>{scale.last_ingest_ms ?? '-'} ms</b>{scale.speedup ? ` (${scale.speedup}x faster)` : ''}.</p>
        <p className="text-xs text-muted">{scale.note}</p>
        <Button variant="ghost" onClick={reset}>Reset demo</Button>
      </Card>
    </div>
  )
}
