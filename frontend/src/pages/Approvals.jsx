import { useCallback, useEffect, useState } from 'react'
import { Check, X } from 'lucide-react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Button, Card, Chip, ErrorBox, Loading, TrustBadge } from '../ui'

export default function Approvals() {
  const { user } = useUser()
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const [done, setDone] = useState({})

  const load = useCallback(() => {
    if (!user) return
    api.approvals(user.person_id).then(setItems).catch((e) => setError(errText(e)))
  }, [user])
  useEffect(load, [load])

  const decide = async (a, decision) => {
    try {
      await api.decide(a.approval_id, user.person_id, decision)
      setDone((d) => ({ ...d, [a.approval_id]: decision === 'approve' ? 'Approved. The previous version was replaced.' : 'Rejected. The author was notified.' }))
      setTimeout(load, 1200)
    } catch (e) { setError(errText(e)) }
  }

  if (!items) return <Loading />
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Approvals for {user.name}</h2>
        <p className="text-sm text-slate-500">Only documents that need a human appear here: they contradict something, or the system is unsure. Nobody approves their own work.</p>
      </div>
      <ErrorBox>{error}</ErrorBox>
      {items.length === 0 && <Card>Nothing needs your attention. That is the goal.</Card>}
      {items.map((a) => (
        <Card key={a.approval_id} className="border-l-4 border-l-sdw-yellow">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs text-slate-500">{a.author.name} ({a.author.role}) asks you to check</p>
              <h3 className="font-semibold">{a.document.title}</h3>
              <p className="text-lg text-sdw-blue">{a.document.key_value}</p>
              <div className="mt-1 flex gap-1.5"><Chip>{a.document.source}</Chip><Chip>{a.document.country}</Chip><Chip>{a.document.topic_name}</Chip></div>
            </div>
            <TrustBadge badge={a.document.badge} score={a.document.trust} />
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-700">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          {done[a.approval_id] ? <p className="mt-3 text-sm font-medium text-emerald-700">{done[a.approval_id]}</p> : (
            <div className="mt-3 flex gap-2">
              <Button variant="good" onClick={() => decide(a, 'approve')}><Check className="h-4 w-4" />Approve</Button>
              <Button variant="bad" onClick={() => decide(a, 'reject')}><X className="h-4 w-4" />Reject</Button>
            </div>
          )}
        </Card>
      ))}
    </div>
  )
}
