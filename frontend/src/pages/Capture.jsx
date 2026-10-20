import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, FilePlus2 } from 'lucide-react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Button, Card, Chip, ErrorBox, SourceChip, TrustBadge } from '../ui'

const field = 'w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent'
const SOURCES = ['SharePoint', 'Teams', 'OneDrive', 'Notion', 'GitHub', 'Legacy drive']

function Result({ res, onSwitch }) {
  if (!res) return null
  return (
    <Card className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-semibold">
          {res.status === 'ignored' && 'Ignored on purpose'}
          {res.status === 'captured' && 'Captured automatically'}
          {res.status === 'published' && 'Captured and published automatically'}
          {res.status === 'pending_approval' && 'Captured, a human check was requested'}
          {res.status === 'duplicate' && 'Already known, nothing added'}
        </h3>
        <Chip>{res.timings_ms_total ?? res.timings_ms} ms</Chip>
      </div>
      {res.reason && <p className="text-sm text-warntext">{res.reason}</p>}
      {res.captured && <p className="text-sm text-muted">Kept: {res.captured}.</p>}
      {res.extracted && res.status === 'captured' && (
        <div className="flex flex-wrap gap-1.5 text-sm">
          <span className="text-muted">Read from the title and description:</span>
          {res.extracted.topic_name && <Chip>topic: {res.extracted.topic_name}</Chip>}
          {res.extracted.country && <Chip>country: {res.extracted.country}</Chip>}
          {res.extracted.client_name && <Chip>customer: {res.extracted.client_name}</Chip>}
          {res.read_from_description?.length > 0 && <span className="text-muted">(found in the description: {res.read_from_description.join(', ')})</span>}
        </div>
      )}
      {res.derived_from_title && Object.keys(res.derived_from_title).length > 0 && (
        <p className="text-sm text-muted">Worked out from the title and folder: {Object.entries(res.derived_from_title).map(([k, v]) => `${k.replace('_id', '')} = ${v}`).join(', ')}.</p>
      )}
      {res.attendees && <p className="text-sm text-muted">{res.attendees.counted} of {res.attendees.invited} attendees counted ({res.attendees.not_opted_in} did not opt in). {res.expertise_updates} expertise updates, so "who knows" changed immediately.</p>}
      {res.document && res.status !== 'duplicate' && (
        <div className="flex items-center justify-between rounded-lg bg-soft p-3 text-sm">
          <span className="min-w-0">{res.document.title}<br /><span className="text-xs text-muted">Find it in: {res.document.location}</span></span>
          {res.document.doc_type !== 'meeting' && <TrustBadge badge={res.document.badge} score={res.document.trust} />}
        </div>
      )}
      {res.metadata && <div className="flex flex-wrap gap-1.5">{Object.entries(res.metadata).filter(([k]) => k !== 'doc_id').map(([k, v]) => <Chip key={k}>{k}: {String(v)}</Chip>)}</div>}
      {res.approval && (
        <div className="space-y-2 text-sm">
          <p>Sent to <b>{res.approval.approver.name}</b>, one level above the author:</p>
          <ul className="list-disc pl-5">{res.approval.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          <Button variant="ghost" onClick={() => onSwitch(res.approval.approver)}>Switch to {res.approval.approver.name} to approve</Button>
        </div>
      )}
    </Card>
  )
}

export default function Capture() {
  const { user, setUser } = useUser()
  const [presets, setPresets] = useState({ documents: [], meetings: [] })
  const [feed, setFeed] = useState([])
  const [members, setMembers] = useState([])
  const [picked, setPicked] = useState([])
  const [meeting, setMeeting] = useState({ title: 'Weekly sync', description: 'Agenda: 1. Nike payroll cut-off in Belgium: agree the new date. 2. Open points from the customer.', as: null })
  const [file, setFile] = useState({ source: 'SharePoint', title: 'Parental leave Belgium (update)', path: '/sites/hr-belgium/Policies/Parental leave Belgium 2026 v5.docx', extract: 'Parental leave. Rule: 18 weeks per parent. Proposed update.', key_value: '18 weeks per parent', as: null })
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')

  const refresh = useCallback(() => api.recentEvents(user.person_id).then(setFeed).catch(() => {}), [user.person_id])
  useEffect(() => { api.presets(user.person_id).then(setPresets).catch(() => {}); refresh() }, [refresh, user.person_id])

  const organizer = meeting.as ?? user.person_id
  useEffect(() => {
    api.teamMembers(organizer).then((m) => { setMembers(m); setPicked(m.slice(0, 4).map((x) => x.person_id)) }).catch(() => setMembers([]))
  }, [organizer])

  const run = async (fn) => {
    setError(''); setRes(null)
    try { setRes(await fn()); refresh() } catch (e) { setError(errText(e)) }
  }
  const sendMeeting = (e) => { e.preventDefault(); run(() => api.sendMeeting({ user_id: organizer, title: meeting.title, description: meeting.description || undefined, attendees: picked })) }
  const sendFile = (e) => {
    e.preventDefault()
    run(() => api.sendEvent({ user_id: file.as ?? user.person_id, source: file.source, title: file.title, path: file.path || undefined, extract: file.extract || undefined, key_value: file.key_value }))
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[26px] font-extrabold">Live capture</h2>
        <p className="text-sm text-muted">Nothing is uploaded here, ever. When someone plans a Teams meeting or saves a file in a connected tool, that tool sends an event. Graphlas keeps the link and the metadata, never the document. This page imitates those events for the demo.</p>
      </div>
      <ErrorBox>{error}</ErrorBox>
      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={sendMeeting} className="space-y-3 rounded-xl border border-line bg-surface p-4">
          <h3 className="flex items-center gap-2 font-semibold"><CalendarClock className="h-5 w-5 text-accent" />Someone plans a Teams meeting</h3>
          <select className={field} defaultValue="" onChange={(e) => { const m = presets.meetings[e.target.value]; setMeeting(m ? { title: m.body.title, description: m.body.description ?? '', as: m.user_id } : { ...meeting, as: null }) }}>
            <option value="">Load an example...</option>
            {presets.meetings.map((m, i) => <option key={m.name} value={i}>{m.name}</option>)}
          </select>
          <input className={field} value={meeting.title} maxLength={200} required onChange={(e) => setMeeting({ ...meeting, title: e.target.value })} aria-label="Meeting title" placeholder="Meeting title" />
          <textarea className={field} rows={3} value={meeting.description} maxLength={1000} onChange={(e) => setMeeting({ ...meeting, description: e.target.value })} aria-label="Meeting description" placeholder="Meeting description or agenda (optional). It is read, never stored." />
          <div>
            <p className="mb-1 text-xs font-semibold uppercase text-muted">Attendees (only people who opted in count)</p>
            <div className="grid gap-1 sm:grid-cols-2">
              {members.map((m) => (
                <label key={m.person_id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={picked.includes(m.person_id)} onChange={() => setPicked(picked.includes(m.person_id) ? picked.filter((x) => x !== m.person_id) : [...picked, m.person_id])} />
                  {m.name}{!m.meetings_opt_in && <span className="text-xs text-muted">(no opt-in)</span>}
                </label>
              ))}
            </div>
          </div>
          <Button type="submit">Plan meeting</Button>
        </form>

        <form onSubmit={sendFile} className="space-y-3 rounded-xl border border-line bg-surface p-4">
          <h3 className="flex items-center gap-2 font-semibold"><FilePlus2 className="h-5 w-5 text-accent" />Someone saves a file in a connected tool</h3>
          <select className={field} defaultValue="" onChange={(e) => { const d = presets.documents[e.target.value]; if (d) setFile({ source: d.body.source, title: d.body.title, path: d.body.path ?? '', extract: d.body.extract ?? '', key_value: d.body.key_value ?? '', as: d.user_id }) }}>
            <option value="">Load an example...</option>
            {presets.documents.map((d, i) => <option key={d.name} value={i}>{d.name}</option>)}
          </select>
          <div className="grid gap-2 sm:grid-cols-2">
            <select className={field} value={file.source} onChange={(e) => setFile({ ...file, source: e.target.value })} aria-label="Tool">{SOURCES.map((s) => <option key={s}>{s}</option>)}</select>
            <input className={field} value={file.title} maxLength={200} required onChange={(e) => setFile({ ...file, title: e.target.value })} placeholder="File name" aria-label="File name" />
            <input className={`${field} sm:col-span-2`} value={file.path} maxLength={300} onChange={(e) => setFile({ ...file, path: e.target.value })} placeholder="Folder path" aria-label="Folder path" />
            <input className={`${field} sm:col-span-2`} value={file.extract} maxLength={300} onChange={(e) => setFile({ ...file, extract: e.target.value })} placeholder="One fact read at the source (optional)" aria-label="Extracted fact" />
          </div>
          <p className="text-xs text-muted">Topic, country and customer are worked out from the title and folder. The fact is one sentence, not the document.</p>
          <Button type="submit">Save file</Button>
        </form>
      </div>

      <Result res={res} onSwitch={(p) => setUser({ ...p, extra: true })} />

      <Card className="space-y-2">
        <h3 className="font-semibold">What was captured recently</h3>
        {feed.length === 0 && <p className="text-sm text-muted">Nothing yet. Send an event above.</p>}
        <ul className="space-y-1 text-sm">
          {feed.map((f, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <SourceChip source={f.source} /><span className="font-medium">{f.title}</span><span className="text-muted">by {f.who}: {f.summary}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
