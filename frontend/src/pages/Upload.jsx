import { useEffect, useState } from 'react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Button, Card, Chip, ErrorBox, TrustBadge } from '../ui'

const empty = { title: '', text: '', source: 'SharePoint', topic_id: '', country: '', client: '', key_value: '' }
const field = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent'

export default function Upload() {
  const { user, setUser } = useUser()
  const [meta, setMeta] = useState(null)
  const [samples, setSamples] = useState([])
  const [form, setForm] = useState(empty)
  const [asUser, setAsUser] = useState(null)
  const [res, setRes] = useState(null)
  const [scale, setScale] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.meta().then(setMeta); api.samples().then(setSamples); api.scale().then(setScale) }, [])
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const loadSample = (i) => {
    if (i === '') { setForm(empty); setAsUser(null); return }
    const s = samples[i]
    setForm({ ...empty, ...s.body, topic_id: s.body.topic_id ?? '', client: s.body.client ?? '' })
    setAsUser(s.body.user_id)
  }

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError(''); setRes(null)
    const body = { user_id: asUser ?? user.person_id, title: form.title, text: form.text, source: form.source, key_value: form.key_value }
    if (form.topic_id) body.topic_id = form.topic_id
    if (form.country) body.country = form.country
    if (form.client) body.client = form.client
    try { setRes(await api.upload(body)); api.scale().then(setScale) }
    catch (err) { setError(errText(err)) }
    finally { setBusy(false) }
  }

  const switchToApprover = () => setUser({ ...res.approval.approver, extra: true })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <form onSubmit={submit} className="space-y-3">
        <div>
          <h2 className="text-[26px] font-extrabold">Add a document</h2>
          <p className="text-sm text-muted">A template for new HR documents. In real life this happens in the tools people already use; the system reads it from there.</p>
        </div>
        <select className={field} onChange={(e) => loadSample(e.target.value)} defaultValue="">
          <option value="">Load a demo example...</option>
          {samples.map((s, i) => <option key={s.name} value={i}>{s.name}</option>)}
        </select>
        <input className={field} placeholder="Title" required maxLength={200} value={form.title} onChange={set('title')} />
        <textarea className={field} rows={4} placeholder="Text" required maxLength={5000} value={form.text} onChange={set('text')} />
        <div className="grid grid-cols-2 gap-3">
          <select className={field} value={form.source} onChange={set('source')}>{meta?.sources.map((s) => <option key={s}>{s}</option>)}</select>
          <input className={field} placeholder='Stated value, e.g. "17 weeks per parent"' maxLength={100} value={form.key_value} onChange={set('key_value')} />
          <select className={field} value={form.topic_id} onChange={set('topic_id')}>
            <option value="">Topic: detect automatically</option>
            {meta?.topics.map((t) => <option key={t.topic_id} value={t.topic_id}>{t.name}</option>)}
          </select>
          <select className={field} value={form.country} onChange={set('country')}>
            <option value="">Country: mine</option>
            {meta?.countries.map((c) => <option key={c.country} value={c.country}>{c.name}</option>)}
          </select>
          <select className={field} value={form.client} onChange={set('client')}>
            <option value="">Customer: none</option>
            {meta?.clients.map((c) => <option key={c.client_id} value={c.client_id}>{c.name}</option>)}
          </select>
        </div>
        <Button type="submit" disabled={busy}>{busy ? 'Checking...' : 'Add document'}</Button>
        <ErrorBox>{error}</ErrorBox>
      </form>

      <div className="space-y-3">
        {res && (
          <Card>
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">
                {res.status === 'published' && 'Published automatically'}
                {res.status === 'pending_approval' && 'Waiting for a human check'}
                {res.status === 'duplicate' && 'Already known, nothing added'}
              </h3>
              <Chip>{res.timings_ms} ms</Chip>
            </div>
            {res.classified && <p className="mt-2 text-sm">Topic detected: <b>{res.classified.topic_name}</b> ({Math.round(res.classified.confidence * 100)}% sure)</p>}
            {res.message && <p className="mt-2 text-sm text-muted">{res.message}</p>}
            {res.document && <div className="mt-3 flex items-center justify-between rounded-lg bg-soft p-3 text-sm"><span>{res.document.title}<br /><span className="text-muted">{res.document.key_value}</span></span><TrustBadge badge={res.document.badge} score={res.document.trust} /></div>}
            {res.approval && (
              <div className="mt-3 space-y-2 text-sm">
                <p>Sent to <b>{res.approval.approver.name}</b> ({res.approval.approver.role}), one level above the author.</p>
                <ul className="list-disc pl-5 text-main">{res.approval.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                <Button variant="ghost" onClick={switchToApprover}>Switch to {res.approval.approver.name} to approve</Button>
              </div>
            )}
          </Card>
        )}
        {scale && (
          <Card>
            <h3 className="font-semibold">Why this is fast</h3>
            <p className="mt-1 text-sm text-muted">A new document is scored by the existing model: {scale.last_ingest_ms ?? 'about 40'} ms. A full rebuild of {scale.documents.toLocaleString()} documents takes {scale.full_rebuild_seconds} s{scale.speedup ? `, so ${scale.speedup}x slower` : ''}. Nobody has to annotate anything.</p>
          </Card>
        )}
      </div>
    </div>
  )
}
