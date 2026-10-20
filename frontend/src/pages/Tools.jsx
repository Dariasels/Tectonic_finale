import { useCallback, useEffect, useState } from 'react'
import { api, errText } from '../api'
import { useUser } from '../user'
import { Card, ErrorBox, Loading, SourceChip } from '../ui'

function Toggle({ checked, onChange, disabled, children }) {
  return (
    <label className={`flex items-center gap-3 rounded-lg border border-line p-2.5 text-sm ${disabled ? 'opacity-70' : 'cursor-pointer'}`}>
      <input type="checkbox" className="h-4 w-4" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />{children}
    </label>
  )
}

export default function Tools() {
  const { user } = useUser()
  const [p, setP] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')

  const load = useCallback(() => {
    if (!user) return
    api.profile(user.person_id).then(setP).catch((e) => setError(errText(e)))
    api.toolsStatus(user.person_id).then(setStatus).catch(() => {})
  }, [user])
  useEffect(load, [load])

  const save = async (body, note) => {
    setError(''); setMsg('')
    try { setP(await api.saveProfile({ user_id: user.person_id, ...body })); setMsg(note); api.toolsStatus(user.person_id).then(setStatus) }
    catch (e) { setError(errText(e)) }
  }
  const enabled = (list) => list.filter((t) => t.enabled).map((t) => t.source)


  if (!p) return <Loading />
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[26px] font-extrabold">Connected tools</h2>
        <p className="text-sm text-muted">Nobody has to move to a new system. The tools your team already uses are read, and only those.</p>
      </div>
      <ErrorBox>{error}</ErrorBox>
      {msg && <p className="text-sm text-oktext">{msg}</p>}
      {p.warnings.map((w) => <div key={w} className="rounded-xl bg-warnbg p-3 text-sm text-warntext ring-1 ring-warn/40">{w}</div>)}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-3">
          <h3 className="font-semibold">Tools of {p.team.name}</h3>
          <p className="text-xs text-muted">{p.can_edit_team ? 'You are a team lead: you decide which tools count for this team.' : 'Only a team lead (or higher) can change this. The server checks it.'}</p>
          <div className="grid gap-2">
            {p.team_tools.map((t) => (
              <Toggle key={t.source} checked={t.enabled} disabled={!p.can_edit_team}
                onChange={(v) => save({ team_tools: v ? [...enabled(p.team_tools), t.source] : enabled(p.team_tools).filter((s) => s !== t.source) }, 'Team tools saved.')}>
                <SourceChip source={t.source} /><span className="text-xs text-muted">{t.note}{t.official ? ', official source' : ''}</span>
              </Toggle>
            ))}
          </div>
        </Card>
        <div className="space-y-4">
          <Card className="space-y-3">
            <h3 className="font-semibold">Your personal tools</h3>
            {p.personal_tools.map((t) => (
              <Toggle key={t.source} checked={t.enabled}
                onChange={(v) => save({ personal_tools: v ? [...enabled(p.personal_tools), t.source] : enabled(p.personal_tools).filter((s) => s !== t.source) }, 'Saved.')}>
                <SourceChip source={t.source} /><span className="text-xs text-muted">{t.note}</span>
              </Toggle>
            ))}
          </Card>
          <Card className="space-y-3">
            <h3 className="font-semibold">Signals from your daily work</h3>
            <p className="text-xs text-muted">Opt-in. Switching one off removes it from the expertise scores right away.</p>
            {p.signals.map((s) => (
              <Toggle key={s.key} checked={s.enabled} onChange={(v) => save({ signals: { [s.key]: v } }, v ? 'Signal on.' : 'Signal off: expertise scores were updated.')}>{s.label}</Toggle>
            ))}
          </Card>
        </div>
      </div>

      {status && (
        <Card className="space-y-2">
          <h3 className="font-semibold">Company-wide: how many teams use each tool</h3>
          <div className="flex flex-wrap gap-2">{Object.entries(status.adoption_teams).map(([s, n]) => <span key={s} className="flex items-center gap-1"><SourceChip source={s} /><span className="text-sm tabular-nums">{n} of {status.teams_total}</span></span>)}</div>
          <p className="text-sm text-muted">{status.teams_without_official_source} teams have no official source connected: their knowledge stays invisible.</p>
        </Card>
      )}

      <Card><p className="text-sm text-muted">Documents are never uploaded here. When someone plans a Teams meeting or saves a file in a connected tool, the tool sends an event and Graphlas keeps the link and metadata. See <b>Live capture</b> to try it.</p></Card>
    </div>
  )
}
