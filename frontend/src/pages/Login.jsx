import { useEffect, useState } from 'react'
import { ArrowRight, Check, Lock } from 'lucide-react'
import { api, errText } from '../api'
import { Header } from '../Header'
import { useUser } from '../user'
import { Button, Card, ErrorBox, SourceChip } from '../ui'

const QUESTIONS = {
  find: 'How do you find answers today?',
  frequency: 'How often do you create or update documents?',
  templates: 'Do you use fixed templates for new documents?',
  versions: 'How do you know which version is the current one?',
}

function Choice({ options, value, onChange, name }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <label key={o} className={`cursor-pointer rounded-full border px-3 py-1 text-sm ${value === o ? 'border-magenta bg-soft font-medium' : 'border-line'}`}>
          <input type="radio" name={name} className="sr-only" checked={value === o} onChange={() => onChange(o)} />{o}
        </label>
      ))}
    </div>
  )
}

function Toggle({ checked, onChange, disabled, label, note }) {
  return (
    <label className={`flex items-start gap-3 rounded-lg border border-line p-3 ${disabled ? 'opacity-70' : 'cursor-pointer'}`}>
      <input type="checkbox" className="mt-1 h-4 w-4" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="text-sm">{label}{note && <span className="block text-xs text-muted">{note}</span>}</span>
    </label>
  )
}

export default function Login({ onDone, initialMode }) {
  const { users, setUser, error: userError } = useUser()
  const [step, setStep] = useState(1)
  const [mode, setMode] = useState(initialMode ?? (new URLSearchParams(window.location.search).has('create') ? 'create' : 'signin'))                 // 'signin' (any colleague) or 'create' (new login)
  const [pick, setPick] = useState(null)
  const [pickCard, setPickCard] = useState(null)
  const [query, setQuery] = useState('')
  const [found, setFound] = useState([])
  const [meta, setMeta] = useState(null)
  const [opts, setOpts] = useState(null)
  const [created, setCreated] = useState(null)
  const [form, setForm] = useState({ name: '', country: 'BE', department: 'HR Advisory', level: 'Junior', team_id: '', new_team_name: '', tools: ['Teams', 'SharePoint'] })
  const [profile, setProfile] = useState(null)
  const [answers, setAnswers] = useState({})
  const [personal, setPersonal] = useState([])
  const [team, setTeam] = useState([])
  const [signals, setSignals] = useState({})
  const [connected, setConnected] = useState({})
  const linkedAccounts = []                                   // accounts are linked later, under Connected tools
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (users.length && !pick) { setPick(users[0].person_id); setPickCard(users[0]) } }, [users, pick])
  useEffect(() => { api.meta().then(setMeta).catch(() => {}) }, [])
  useEffect(() => {                                           // teams of the chosen country and department
    if (mode !== 'create') return
    api.signupOptions(form.country, form.department).then((o) => { setOpts(o); setForm((f) => ({ ...f, team_id: o.teams[0]?.team_id ?? '' })) }).catch(() => setOpts(null))
  }, [mode, form.country, form.department])
  useEffect(() => {                                           // search all colleagues by name
    if (query.trim().length < 2) { setFound([]); return }
    const t = setTimeout(() => api.searchPeople(query.trim()).then(setFound).catch(() => setFound([])), 250)
    return () => clearTimeout(t)
  }, [query])

  const next = async () => {
    setError('')
    if (step === 1) {
      try {
        let id = pick
        if (mode === 'create' && !created) {
          const body = { name: form.name, country: form.country, department: form.department, level: form.level }
          if (form.team_id === '__new') { body.new_team_name = form.new_team_name; body.team_tools = form.tools } else body.team_id = form.team_id
          const c = await api.signup(body)
          setCreated(c); setPick(c.person.person_id); setPickCard({ ...c.person, extra: true }); id = c.person.person_id
        } else if (mode === 'create') id = created.person.person_id
        const p = await api.profile(id)
        setProfile(p)
        setAnswers(p.answers ?? {})
        setPersonal([...new Set([...p.personal_tools.filter((t) => t.enabled).map((t) => t.source), ...(linkedAccounts.includes('Notion') ? ['Notion'] : [])])])
        setTeam(p.team_tools.filter((t) => t.enabled).map((t) => t.source))
        setSignals({ ...Object.fromEntries(p.signals.map((s) => [s.key, s.enabled])), ...(linkedAccounts.includes('GitHub') ? { commits: true } : {}), ...(linkedAccounts.includes('Teams') ? { meetings: true } : {}) })
        setStep(2)
      } catch (e) { setError(errText(e)) }
    } else setStep(step + 1)
  }

  const finish = async () => {
    setBusy(true); setError('')
    try {
      const body = { user_id: pick, personal_tools: personal, signals, answers, connections: linkedAccounts }
      if (profile.can_edit_team && !created?.team?.created) body.team_tools = team
      await api.saveProfile(body)
      onDone({ ...pickCard, extra: true })
    } catch (e) { setError(errText(e)) } finally { setBusy(false) }
  }

  const toggleIn = (list, set, v) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v])
  const allTools = [...new Set([...team, ...personal])]

  return (
    <div className="min-h-screen">
      <Header right={null} />
      <main className="mx-auto max-w-2xl space-y-4 px-4 py-6">
        <div>
          <h2 className="text-[26px] font-extrabold">{step === 1 ? (mode === 'create' ? 'Create a login' : 'Sign in') : step === 2 ? 'Your tools and how you work' : 'Privacy and connections'}</h2>
          <p className="text-sm text-muted">Step {step} of 3. This takes a minute, and you can change everything later under Connected tools.</p>
        </div>
        <ErrorBox>{error || userError}</ErrorBox>

        {step === 1 && (
          <Card className="space-y-4">
            <div className="flex gap-2 text-sm" role="tablist">
              {[['signin', 'Sign in'], ['create', 'Create a new login']].map(([k, l]) => (
                <button key={k} role="tab" aria-selected={mode === k} onClick={() => { setMode(k); setError('') }}
                  className={`rounded-lg px-3 py-1.5 font-medium ${mode === k ? 'border-b-2 border-magenta bg-soft' : 'text-muted hover:bg-soft'}`}>{l}</button>
              ))}
            </div>

            {mode === 'signin' && (
              <>
                <p className="text-sm text-muted">Demo sign-in with a work account: search any of the {users.length ? '10,000+' : ''} colleagues by name. There is no password in this proof of concept.</p>
                <input className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent" placeholder="Search your name, for example Sofie" value={query} maxLength={60}
                  onChange={(e) => setQuery(e.target.value)} aria-label="Search your name" />
                {found.map((u) => (
                  <label key={u.person_id} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${pick === u.person_id ? 'border-magenta bg-soft' : 'border-line'}`}>
                    <input type="radio" name="who" checked={pick === u.person_id} onChange={() => { setPick(u.person_id); setPickCard({ ...u, extra: true }) }} />
                    <span className="text-sm"><b>{u.name}</b> <span className="text-muted">{u.role}, {u.department}, {u.country}</span><span className="block text-xs text-muted">{u.team}</span></span>
                  </label>
                ))}
                {query.trim().length >= 2 && found.length === 0 && <p className="text-sm text-muted">No colleague found.</p>}
                <p className="pt-1 text-xs font-semibold uppercase text-muted">Or pick a demo colleague</p>
                {users.map((u) => (
                  <label key={u.person_id} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${pick === u.person_id ? 'border-magenta bg-soft' : 'border-line'}`}>
                    <input type="radio" name="who" checked={pick === u.person_id} onChange={() => { setPick(u.person_id); setPickCard(u) }} />
                    <span className="text-sm"><b>{u.name}</b> <span className="text-muted">{u.role}, {u.department}, {u.country}</span><span className="block text-xs text-muted">{u.label}</span></span>
                  </label>
                ))}
                {users.length === 0 && <p className="text-sm text-muted">Starting the backend (about 10 seconds)...</p>}
              </>
            )}

            {mode === 'create' && (
              <div className="space-y-3">
                <p className="text-sm text-muted">New to Graphlas? Create a login and join your team. A team lead can create a new team and choose its tools.</p>
                {[['name', 'Full name']].map(([k, l]) => (
                  <label key={k} className="block text-sm"><span className="mb-1 block font-medium">{l}</span>
                    <input className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent" value={form[k]} maxLength={60} onChange={(e) => setForm({ ...form, [k]: e.target.value })} /></label>
                ))}
                <div className="grid gap-3 sm:grid-cols-3">
                  <label className="block text-sm"><span className="mb-1 block font-medium">Country</span>
                    <select className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm" value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}>{meta?.countries.map((c) => <option key={c.country} value={c.country}>{c.name}</option>)}</select></label>
                  <label className="block text-sm"><span className="mb-1 block font-medium">Department</span>
                    <select className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })}>{(opts?.departments ?? [form.department]).map((d) => <option key={d}>{d}</option>)}</select></label>
                  <label className="block text-sm"><span className="mb-1 block font-medium">Level</span>
                    <select className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm" value={form.level} onChange={(e) => setForm({ ...form, level: e.target.value, team_id: e.target.value !== 'Team Lead' && form.team_id === '__new' ? (opts?.teams[0]?.team_id ?? '') : form.team_id })}>{(opts?.levels ?? ['Junior', 'Medior', 'Senior', 'Team Lead']).map((l) => <option key={l}>{l}</option>)}</select></label>
                </div>
                <label className="block text-sm"><span className="mb-1 block font-medium">Team</span>
                  <select className="w-full rounded-lg border border-line bg-surface px-2 py-2 text-sm" value={form.team_id} onChange={(e) => setForm({ ...form, team_id: e.target.value })}>
                    {opts?.teams.map((t) => <option key={t.team_id} value={t.team_id}>{t.name} ({t.people} people{t.has_lead ? '' : ', no team lead'})</option>)}
                    {form.level === 'Team Lead' && <option value="__new">Create a new team...</option>}
                  </select></label>
                {form.team_id === '__new' && (
                  <div className="space-y-2 rounded-lg border border-line p-3">
                    <label className="block text-sm"><span className="mb-1 block font-medium">Name of the new team</span>
                      <input className="w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent" value={form.new_team_name} maxLength={60} onChange={(e) => setForm({ ...form, new_team_name: e.target.value })} /></label>
                    <p className="text-sm font-medium">Which tools does your team use?</p>
                    <div className="grid gap-2 sm:grid-cols-2">
                      {(opts?.sources ?? []).map((t) => (
                        <label key={t} className="flex cursor-pointer items-center gap-2 text-sm"><input type="checkbox" checked={form.tools.includes(t)} onChange={() => setForm({ ...form, tools: form.tools.includes(t) ? form.tools.filter((x) => x !== t) : [...form.tools, t] })} /><SourceChip source={t} /></label>
                      ))}
                    </div>
                  </div>
                )}
                {created && <p className="text-sm text-oktext">Login created for {created.person.name}.</p>}
              </div>
            )}
          </Card>
        )}

        {step === 2 && profile && (
          <>
            <Card className="space-y-4">
              <h3 className="font-semibold">A few questions</h3>
              {Object.entries(QUESTIONS).map(([k, q]) => (
                <div key={k} className="space-y-1.5">
                  <p className="text-sm font-medium">{q}</p>
                  <Choice name={k} options={profile.questions[k]} value={answers[k]} onChange={(v) => setAnswers({ ...answers, [k]: v })} />
                </div>
              ))}
            </Card>
            <Card className="space-y-3">
              <h3 className="font-semibold">Tools of {profile.team.name}</h3>
              {!profile.can_edit_team && <p className="text-sm text-muted">Your team lead manages these. You can see what is connected.</p>}
              <div className="grid gap-2 sm:grid-cols-2">
                {profile.team_tools.map((t) => (
                  <Toggle key={t.source} checked={team.includes(t.source)} disabled={!profile.can_edit_team}
                    onChange={() => toggleIn(team, setTeam, t.source)} label={<SourceChip source={t.source} />} note={t.note} />
                ))}
              </div>
            </Card>
            <Card className="space-y-3">
              <h3 className="font-semibold">Your personal tools</h3>
              <p className="text-sm text-muted">Optional. Only if you want your own notes to count as knowledge for colleagues.</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {profile.personal_tools.map((t) => (
                  <Toggle key={t.source} checked={personal.includes(t.source)} onChange={() => toggleIn(personal, setPersonal, t.source)}
                    label={<SourceChip source={t.source} />} note={t.note} />
                ))}
              </div>
            </Card>
          </>
        )}

        {step === 3 && profile && (
          <>
            <Card className="space-y-3">
              <h3 className="flex items-center gap-2 font-semibold"><Lock className="h-4 w-4" />Signals from your daily work</h3>
              <p className="text-sm text-muted">Optional and off unless you switch them on. They help find who knows what. You can change this at any time.</p>
              {profile.signals.map((s) => (
                <Toggle key={s.key} checked={!!signals[s.key]} onChange={(v) => setSignals({ ...signals, [s.key]: v })} label={s.label} />
              ))}
              <p className="text-xs text-muted">What is kept: the title, tool, author, team, country, dates, version and access rights of a document, plus what is needed to score it. Documents you may not see are never shown to others.</p>
            </Card>
            {created?.team?.created && (
              <Card className="space-y-2">
                <h3 className="font-semibold">Connect links for {created.team.name}</h3>
                <p className="text-sm text-muted">Share these with your team so each tool can be connected. Simulated in this demo.</p>
                {Object.entries(created.connect_links).map(([tool, url]) => <p key={tool} className="flex flex-wrap items-center gap-2 text-sm"><SourceChip source={tool} /><span className="break-all font-mono text-xs">{url}</span></p>)}
              </Card>
            )}
            {linkedAccounts.length > 0 && (
              <Card className="space-y-1">
                <h3 className="font-semibold">Accounts you linked on the first page</h3>
                <p className="text-sm text-muted">{linkedAccounts.join(', ')}. Linking them switched on what they read (shown below), and you can change that.</p>
              </Card>
            )}
            <Card className="space-y-3">
              <h3 className="font-semibold">Connect your tools</h3>
              <p className="text-sm text-muted">In this demo the connections are simulated. In production this is where each tool asks for permission.</p>
              {allTools.length === 0 && <p className="text-sm text-muted">No tools selected.</p>}
              {allTools.map((s) => (
                <div key={s} className="flex items-center justify-between rounded-lg border border-line p-2">
                  <SourceChip source={s} />
                  {connected[s] ? <span className="flex items-center gap-1 text-sm text-oktext"><Check className="h-4 w-4" />Connected</span>
                    : <Button variant="ghost" onClick={() => setConnected({ ...connected, [s]: true })}>Connect</Button>}
                </div>
              ))}
            </Card>
          </>
        )}

        <div className="flex justify-between">
          <Button variant="ghost" disabled={step === 1} onClick={() => setStep(step - 1)}>Back</Button>
          {step < 3 ? <Button onClick={next} disabled={mode === 'signin' ? !pick : !(created || form.name.trim().length >= 2)}>Next<ArrowRight className="h-4 w-4" /></Button>
            : <Button onClick={finish} disabled={busy}>{busy ? 'Saving...' : 'Enter Graphlas'}</Button>}
        </div>
      </main>
    </div>
  )
}
