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

export default function Login({ onDone }) {
  const { users, setUser, error: userError } = useUser()
  const [step, setStep] = useState(1)
  const [pick, setPick] = useState(null)
  const [profile, setProfile] = useState(null)
  const [answers, setAnswers] = useState({})
  const [personal, setPersonal] = useState([])
  const [team, setTeam] = useState([])
  const [signals, setSignals] = useState({})
  const [connected, setConnected] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { if (users.length && !pick) setPick(users[0].person_id) }, [users, pick])

  const next = async () => {
    setError('')
    if (step === 1) {
      try {
        const p = await api.profile(pick)
        setProfile(p)
        setAnswers(p.answers ?? {})
        setPersonal(p.personal_tools.filter((t) => t.enabled).map((t) => t.source))
        setTeam(p.team_tools.filter((t) => t.enabled).map((t) => t.source))
        setSignals(Object.fromEntries(p.signals.map((s) => [s.key, s.enabled])))
        setStep(2)
      } catch (e) { setError(errText(e)) }
    } else setStep(step + 1)
  }

  const finish = async () => {
    setBusy(true); setError('')
    try {
      const body = { user_id: pick, personal_tools: personal, signals, answers }
      if (profile.can_edit_team) body.team_tools = team
      await api.saveProfile(body)
      const person = users.find((u) => u.person_id === pick)
      onDone(person)
    } catch (e) { setError(errText(e)) } finally { setBusy(false) }
  }

  const toggleIn = (list, set, v) => set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v])
  const allTools = [...new Set([...team, ...personal])]

  return (
    <div className="min-h-screen">
      <Header right={null} />
      <main className="mx-auto max-w-2xl space-y-4 px-4 py-6">
        <div>
          <h2 className="text-[26px] font-extrabold">{step === 1 ? 'Sign in' : step === 2 ? 'Your tools and how you work' : 'Privacy and connections'}</h2>
          <p className="text-sm text-muted">Step {step} of 3. This takes a minute, and you can change everything later under Connected tools.</p>
        </div>
        <ErrorBox>{error || userError}</ErrorBox>

        {step === 1 && (
          <Card className="space-y-3">
            <p className="text-sm text-muted">Demo sign-in: pick a colleague. There is no password in this proof of concept.</p>
            {users.map((u) => (
              <label key={u.person_id} className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 ${pick === u.person_id ? 'border-magenta bg-soft' : 'border-line'}`}>
                <input type="radio" name="who" checked={pick === u.person_id} onChange={() => setPick(u.person_id)} />
                <span className="text-sm"><b>{u.name}</b> <span className="text-muted">{u.role}, {u.department}, {u.country}</span><span className="block text-xs text-muted">{u.label}</span></span>
              </label>
            ))}
            {users.length === 0 && <p className="text-sm text-muted">Starting the backend (about 10 seconds)...</p>}
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
          {step < 3 ? <Button onClick={next} disabled={!pick}>Next<ArrowRight className="h-4 w-4" /></Button>
            : <Button onClick={finish} disabled={busy}>{busy ? 'Saving...' : 'Enter Graphlas'}</Button>}
        </div>
      </main>
    </div>
  )
}
