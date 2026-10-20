import { useCallback, useEffect, useState } from 'react'
import { Check, FileText, MapPin, RotateCcw, Trash2, X } from 'lucide-react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Button, Card, Chip, ErrorBox, Loading, TrustBadge } from '../ui'

function ApprovalCard({ a, onDecide, done }) {
  return (
    <Card className="border-l-4 border-l-magenta">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs text-muted">{a.author.name} ({a.author.role}) asks you to check</p>
          <h3 className="font-semibold">{a.document.title}</h3>
          <p className="text-lg text-accent">{a.document.key_value}</p>
          <p className="mt-1 text-sm text-muted">Find it in: {a.document.location}</p>
          <div className="mt-1 flex gap-1.5"><Chip>{a.document.source}</Chip><Chip>{a.document.country}</Chip><Chip>{a.document.topic_name}</Chip></div>
        </div>
        <TrustBadge badge={a.document.badge} score={a.document.trust} />
      </div>
      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      {done ? <p className="mt-3 text-sm font-medium text-oktext">{done}</p> : (
        <div className="mt-3 flex gap-2">
          <Button variant="good" onClick={() => onDecide(a, 'approve')}><Check className="h-4 w-4" />Approve</Button>
          <Button variant="bad" onClick={() => onDecide(a, 'reject')}><X className="h-4 w-4" />Reject</Button>
        </div>
      )}
    </Card>
  )
}

/* A very low score: the team lead is asked, with the reasons, whether the document can go. Nothing is removed without an answer. */
function ReviewCard({ a, onDecide, done }) {
  return (
    <Card className="border-l-4 border-l-bad">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-semibold uppercase text-muted">Clean-up review</p>
          <h3 className="text-lg font-extrabold">Do you want to remove this document?</h3>
          <p className="flex items-center gap-1.5"><FileText className="h-4 w-4 shrink-0 text-muted" /><span className="font-medium">{a.document.title}</span></p>
          <p className="flex items-center gap-1.5 text-sm text-muted"><MapPin className="h-4 w-4 shrink-0" />Find it in: {a.document.location}</p>
        </div>
        <TrustBadge badge={a.document.badge} score={a.document.trust} />
      </div>
      <p className="mt-3 text-sm font-medium">Because:</p>
      <ul className="list-disc space-y-1 pl-5 text-sm">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      <p className="mt-2 text-xs text-muted">Removing only hides it in Graphlas. The file itself stays where it is, and you can restore it below.</p>
      {done ? <p className="mt-3 text-sm font-medium text-oktext">{done}</p> : (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button variant="bad" onClick={() => onDecide(a, 'remove')}><Trash2 className="h-4 w-4" />Yes, remove it</Button>
          <Button variant="good" onClick={() => onDecide(a, 'keep')}><Check className="h-4 w-4" />No, keep it: it is reliable</Button>
        </div>
      )}
    </Card>
  )
}

export default function Approvals() {
  const { user } = useUser()
  const [items, setItems] = useState(null)
  const [log, setLog] = useState([])
  const [error, setError] = useState('')
  const [done, setDone] = useState({})

  const load = useCallback(() => {
    if (!user) return
    api.approvals(user.person_id).then(setItems).catch((e) => setError(errText(e)))
    api.cleanupLog(user.person_id).then(setLog).catch(() => setLog([]))          // only team leads and technical people see the log
  }, [user])
  useEffect(load, [load])

  const decide = async (a, decision) => {
    try {
      await api.decide(a.approval_id, user.person_id, decision)
      const text = { approve: 'Approved. The previous version was replaced and removed from Graphlas.', reject: 'Rejected. The author was notified.',
        keep: 'Kept. It now counts as verified by you.', remove: 'Removed from Graphlas. The file itself was not touched.' }[decision]
      setDone((d) => ({ ...d, [a.approval_id]: text }))
      setTimeout(load, 1200)
    } catch (e) { setError(errText(e)) }
  }
  const restore = async (docId) => {
    try { await api.restore(docId, user.person_id); load() } catch (e) { setError(errText(e)) }
  }

  if (!items) return <Loading />
  const approvals = items.filter((i) => i.kind !== 'review')
  const reviews = items.filter((i) => i.kind === 'review')
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[26px] font-extrabold">For {user.name}</h2>
        <p className="text-sm text-muted">Only what needs a human appears here: a conflict with a verified document, or a document whose score is very low. Nobody approves their own work.</p>
      </div>
      <ErrorBox>{error}</ErrorBox>
      {items.length === 0 && <Card>Nothing needs your attention. That is the goal.</Card>}
      {approvals.length > 0 && <h3 className="font-semibold">Approvals ({approvals.length})</h3>}
      {approvals.map((a) => <ApprovalCard key={a.approval_id} a={a} onDecide={decide} done={done[a.approval_id]} />)}
      {reviews.length > 0 && <h3 className="font-semibold">Clean-up reviews ({reviews.length})</h3>}
      {reviews.map((a) => <ReviewCard key={a.approval_id} a={a} onDecide={decide} done={done[a.approval_id]} />)}

      {log.length > 0 && (
        <Card className="space-y-2">
          <h3 className="font-semibold">Removed from Graphlas automatically</h3>
          <p className="text-xs text-muted">Replaced documents and documents nobody uses or looks after any more. They can be restored.</p>
          <ul className="space-y-2 text-sm">
            {log.slice(0, 8).map((e) => (
              <li key={e.doc_id + e.when} className="flex flex-wrap items-center justify-between gap-2">
                <span className="min-w-0">
                  <b>{e.title}</b> <span className="text-muted">({e.location})</span>
                  <span className="block text-xs text-muted">{e.reason}{e.successor_title ? ` Replaced by: ${e.successor_title}.` : ''}{e.links_redirected ? ` ${e.links_redirected} links now point to the new one.` : ''} By {e.by_name}, {e.when}.</span>
                </span>
                {e.restored ? <Chip>restored</Chip> : <Button variant="ghost" onClick={() => restore(e.doc_id)}><RotateCcw className="h-4 w-4" />Restore</Button>}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
