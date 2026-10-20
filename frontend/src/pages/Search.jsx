import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, Flag, Search as SearchIcon, ShieldCheck, ThumbsUp, UserCheck, Users } from 'lucide-react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Button, Card, Chip, ErrorBox, Reasons, SourceChip, TrustBadge } from '../ui'

const FEATURED = [
  'How much parental leave do I get in Belgium?',
  'What do we know about Nike?',
  'payroll cut-off for Nike in Belgium',
  'What is the retirement age in Belgium?',
  'salary bands in Poland',
]

function PersonLine({ p }) {
  if (!p) return <span className="text-muted">no owner</span>
  return (
    <span className={p.active ? '' : 'text-muted line-through'}>
      {p.name} <span className="text-xs text-muted">({p.department}, {p.country})</span>
      {!p.active && <span className="ml-1 text-xs no-underline text-badtext"> left the company</span>}
    </span>
  )
}

function ResultCard({ r, user, intent, onChanged }) {
  const [open, setOpen] = useState(false)
  const [msg, setMsg] = useState('')
  const vote = async (kind) => {
    try {
      const updated = await api.vote(r.doc_id, user.person_id, kind)
      onChanged(updated)
      setMsg(kind === 'confirm' ? 'Thanks, confirmed.' : 'Thanks, flagged.')
    } catch (e) { setMsg(errText(e)) }
  }
  return (
    <Card className={r.in_scope ? '' : 'opacity-70'}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{r.title}</h3>
            {r.verified && <span className="inline-flex items-center gap-1 text-xs font-medium text-oktext"><ShieldCheck className="h-4 w-4" />Verified</span>}
            {r.pending_approval && <Chip className="bg-warnbg text-warntext">awaiting approval</Chip>}
          </div>
          {r.key_value && <p className="mt-1 text-lg text-accent">{r.key_value}</p>}
          <div className="mt-2 flex flex-wrap gap-1.5">
            <SourceChip source={r.source} />
            <Chip>{r.country}</Chip>
            {r.client_name && <Chip>{r.client_name}</Chip>}
            <Chip>updated {r.last_modified}</Chip>
            {!r.in_scope && <Chip className="bg-badbg text-badtext">other country</Chip>}
          </div>
          <p className="mt-2 text-sm text-muted">Author: <PersonLine p={r.author} /></p>
          {r.link && <p className="break-all font-mono text-xs text-muted">{r.link}</p>}
          {r.approved_by && <p className="text-sm text-muted">Verified by: <PersonLine p={r.approved_by} /></p>}
        </div>
        <TrustBadge badge={r.badge} score={r.trust} />
      </div>
      <button className="mt-3 flex items-center gap-1 text-sm font-medium text-accent" onClick={() => setOpen(!open)}>
        Why this score? {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="mt-2 space-y-3 rounded-lg bg-soft p-3">
          <Reasons reasons={r.reasons} />
          {r.contributions && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase text-muted">Biggest model signals</p>
              <div className="flex flex-wrap gap-1.5">
                {r.contributions.map((c) => <Chip key={c.label} className={c.effect > 0 ? 'bg-okbg text-oktext' : 'bg-badbg text-badtext'}>{c.label}</Chip>)}
              </div>
            </div>
          )}
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => vote('confirm')}><ThumbsUp className="h-4 w-4" />Confirm</Button>
            <Button variant="ghost" onClick={() => vote('flag')}><Flag className="h-4 w-4" />Flag as wrong</Button>
            <span className="text-sm text-muted">{msg}</span>
          </div>
        </div>
      )}
    </Card>
  )
}

function Experts({ experts, intent, user }) {
  const [done, setDone] = useState({})
  const helped = async (p) => {
    try {
      await api.resolve({ user_id: user.person_id, topic: intent.topic, country: intent.country, client: intent.client, person_id: p.person_id })
      setDone((d) => ({ ...d, [p.person_id]: 'Saved: the next colleague will see this contact first.' }))
    } catch (e) { setDone((d) => ({ ...d, [p.person_id]: errText(e) })) }
  }
  if (!experts.length) return null
  return (
    <Card>
      <h3 className="mb-2 flex items-center gap-2 font-semibold"><Users className="h-5 w-5 text-accent" />Who knows this?</h3>
      <ul className="space-y-3">
        {experts.map((p) => (
          <li key={p.person_id} className="text-sm">
            <div className="flex items-center justify-between gap-2">
              <div><span className="font-medium">{p.name}</span> <span className="text-muted">{p.role}, {p.country}</span></div>
              <Button variant="ghost" className="shrink-0 whitespace-nowrap" onClick={() => helped(p)}><UserCheck className="h-4 w-4" />This helped</Button>
            </div>
            <div className="mt-1 flex flex-wrap gap-1">{p.evidence.map((e) => <Chip key={e}>{e}</Chip>)}</div>
            {p.moved_from && <p className="text-xs text-muted">Moved from {p.moved_from}</p>}
            {done[p.person_id] && <p className="mt-1 text-xs text-oktext">{done[p.person_id]}</p>}
          </li>
        ))}
      </ul>
    </Card>
  )
}

function MiniGraph({ graph }) {
  if (!graph?.nodes?.length) return null
  const docs = graph.nodes.filter((n) => n.type === 'document').slice(0, 5)
  const docIds = new Set(docs.map((n) => n.id))
  const edges = graph.edges.filter((e) => (docIds.has(e.target) && (docIds.has(e.source) || graph.nodes.some((n) => n.id === e.source && n.type === 'person'))))
  const personIds = new Set(edges.map((e) => e.source).filter((id) => !docIds.has(id)))
  const people = graph.nodes.filter((n) => n.type === 'person' && personIds.has(n.id))
  const h = Math.max(people.length, docs.length) * 44 + 20
  const pos = {}
  people.forEach((n, i) => { pos[n.id] = [150, 30 + i * 44] })
  docs.forEach((n, i) => { pos[n.id] = [330, 30 + i * 44] })
  const color = { green: '#1E9E5A', yellow: '#E0A800', red: '#D63031' }
  return (
    <Card>
      <h3 className="mb-2 font-semibold">How these sources connect</h3>
      <svg viewBox={`0 0 560 ${h}`} className="w-full text-main">
        {edges.filter((e) => pos[e.source] && pos[e.target]).map((e, i) => {
          const [x1, y1] = pos[e.source], [x2, y2] = pos[e.target]
          const dash = e.type === 'LINKS_TO' ? '4 3' : e.type === 'SUPERSEDES' ? '1 3' : ''
          const stroke = e.type === 'APPROVED' ? '#1E9E5A' : e.type === 'SUPERSEDES' ? '#D63031' : '#A9A3C2'
          return <path key={i} d={`M${x1 + 6},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2 + (x1 === x2 ? 90 : 0)},${y2} ${x2 - 6},${y2}`} fill="none" stroke={stroke} strokeDasharray={dash} strokeWidth="1.5" />
        })}
        {people.map((n) => <g key={n.id}><circle cx={pos[n.id][0]} cy={pos[n.id][1]} r="6" fill={n.active ? '#7B2FBE' : '#A9A3C2'} /><text x={pos[n.id][0] - 12} y={pos[n.id][1] + 4} textAnchor="end" fontSize="13" fill="currentColor">{n.label}</text></g>)}
        {docs.map((n) => <g key={n.id}><rect x={pos[n.id][0] - 6} y={pos[n.id][1] - 6} width="12" height="12" rx="3" fill={color[n.badge]} /><text x={pos[n.id][0] + 12} y={pos[n.id][1] + 4} fontSize="13" fill="currentColor">{n.label.slice(0, 22)}</text></g>)}
      </svg>
      <p className="text-xs text-muted">Solid: wrote or verified. Dashed: links to. Dotted red: replaced by.</p>
    </Card>
  )
}

export default function Search() {
  const { user } = useUser()
  const [q, setQ] = useState('')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  const { users, setUser } = useUser()
  const [library, setLibrary] = useState([])
  const [showLib, setShowLib] = useState(false)
  useEffect(() => { api.questions().then(setLibrary).catch(() => {}) }, [])

  const run = async (text, asUserId) => {
    if (!user) return
    setLoading(true); setError('')
    try { setData(await api.search({ q: text, user_id: asUserId ?? user.person_id })) }
    catch (e) { setError(errText(e)) }
    finally { setLoading(false) }
  }
  useEffect(() => { setData(null) }, [user?.person_id])
  useEffect(() => { inputRef.current?.focus() }, [])
  useEffect(() => {                       // deep link: /?q=parental+leave+in+Belgium runs the search directly
    const initial = new URLSearchParams(window.location.search).get('q')
    if (initial && user) { setQ(initial); run(initial) }
  }, [user?.person_id])

  const replaceResult = (updated) => setData((d) => ({ ...d, results: d.results.map((r) => (r.doc_id === updated.doc_id ? { ...r, ...updated, reasons: updated.reasons, contributions: r.contributions } : r)) }))

  return (
    <div className="space-y-4">
      <form onSubmit={(e) => { e.preventDefault(); run(q) }} className="flex gap-2">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-3 h-5 w-5 text-muted" />
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} maxLength={300}
            placeholder="Ask anything, e.g. parental leave in Belgium, or what do we know about Nike?"
            className="w-full rounded-xl border border-line bg-surface py-2.5 pl-10 pr-3 text-base shadow-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/30" />
        </div>
        <Button type="submit" className="px-5">Search</Button>
      </form>
      <div className="flex flex-wrap gap-2">
        {FEATURED.map((ex) => <button key={ex} onClick={() => { setQ(ex); run(ex) }} className="rounded-full bg-surface px-3 py-1 text-sm text-muted ring-1 ring-line hover:bg-soft">{ex}</button>)}
        {library.length > 0 && <button onClick={() => setShowLib(!showLib)} className="rounded-full px-3 py-1 text-sm font-medium text-accent hover:underline">{showLib ? 'Hide' : `More example questions (${library.length})`}</button>}
      </div>
      {showLib && (
        <Card className="space-y-3">
          <p className="text-xs text-muted">Each question switches to the colleague who would ask it, so you can see their access rights.</p>
          {[...new Set(library.map((x) => x.category))].map((cat) => (
            <div key={cat}>
              <p className="mb-1 text-xs font-semibold uppercase text-muted">{cat}</p>
              <div className="flex flex-wrap gap-1.5">
                {library.filter((x) => x.category === cat).map((x) => (
                  <button key={x.text + x.persona} title={x.persona_label} onClick={() => {
                    const u = users.find((u) => u.person_id === x.persona)
                    if (u) setUser(u)
                    setQ(x.text); run(x.text, x.persona ?? undefined)
                  }} className="rounded-full bg-soft px-2.5 py-0.5 text-xs text-main ring-1 ring-line hover:bg-soft">{x.text}</button>
                ))}
              </div>
            </div>
          ))}
        </Card>
      )}
      <ErrorBox>{error}</ErrorBox>
      {loading && <p className="text-sm text-muted">Searching...</p>}
      {data && (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-2">
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
              {data.intent.topic_name && <Chip>Topic: {data.intent.topic_name}</Chip>}
              {data.intent.country && <Chip>Country: {data.intent.country}{data.intent.country_defaulted ? ' (your country)' : ''}</Chip>}
              {data.intent.client_name && <Chip>Customer: {data.intent.client_name}</Chip>}
              <span>{data.results.length} results in {data.timings_ms} ms{data.related_notes ? `, ${data.related_notes} loose notes hidden` : ''}</span>
            </div>
            {data.did_you_mean?.length > 0 && (
              <div className="rounded-xl bg-soft p-3 text-sm text-main">
                Did you mean:{' '}
                {data.did_you_mean.map((d) => <button key={d.topic_id} className="mr-2 font-medium text-accent hover:underline" onClick={() => { setQ(d.name); run(d.name) }}>{d.name}</button>)}
              </div>
            )}
            {data.banner && (
              <div className="flex items-start gap-2 rounded-xl bg-badbg p-3 text-sm text-badtext ring-1 ring-bad/30">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" /><span>{data.banner.message}</span>
              </div>
            )}
            {data.ask_expert && (
              <div className="rounded-xl bg-warnbg p-3 text-sm text-warntext ring-1 ring-warn/40">
                No document can be trusted for this question. Ask one of the people on the right.
              </div>
            )}
            {data.shortcuts.map((s, i) => (
              <div key={i} className="rounded-xl bg-okbg p-3 text-sm text-oktext ring-1 ring-ok/30">
                <b>Shortcut:</b> {s.type === 'person' ? `${s.person.name} (${s.person.role}, ${s.person.country})` : s.document.title}. {s.message}.
              </div>
            ))}
            {data.results.length === 0 && <Card>No results you have access to.</Card>}
            {data.results.map((r) => <ResultCard key={r.doc_id} r={r} user={user} intent={data.intent} onChanged={replaceResult} />)}
          </div>
          <div className="space-y-3">
            <Experts experts={data.experts} intent={data.intent} user={user} />
            <MiniGraph graph={data.graph} />
          </div>
        </div>
      )}
    </div>
  )
}
