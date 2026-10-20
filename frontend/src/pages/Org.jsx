import { useEffect, useState } from 'react'
import { api, errText } from '../api'
import { useT } from '../i18n'
import { Card, Chip, ErrorBox, HealthBar, Loading } from '../ui'

export default function Org() {
  const t = useT()
  const [view, setView] = useState('country')       // company-wide view: by country or by department
  const [path, setPath] = useState([])          // [] -> countries, [cc] -> departments, [cc, dept] -> teams, [cc, dept, team] -> team
  const [data, setData] = useState(null)
  const [risks, setRisks] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    const [cc, dept, team] = path
    const req = team ? api.orgTeam(team) : dept ? api.orgDepartment(cc, dept) : cc ? api.orgCountry(cc) : view === 'department' ? api.orgDepartments() : api.orgOverview()
    req.then(setData).catch((e) => setError(errText(e)))
    api.risks(cc).then(setRisks).catch(() => {})
  }, [path, view])

  const crumbs = ['Europe', ...path]
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-[26px] font-extrabold">{t('nav_org')}</h2>
        <p className="text-sm text-muted">Health = average trust score of the documents a unit owns. Click to drill down: country, department, team.</p>
      </div>
      {path.length === 0 && (
        <div className="flex gap-2 text-sm" role="tablist">
          {[['country', t('org_by_country')], ['department', t('org_by_dept')]].map(([k, l]) => (
            <button key={k} role="tab" aria-selected={view === k} onClick={() => setView(k)} className={`rounded-lg px-3 py-1.5 font-medium ${view === k ? 'border-b-2 border-magenta bg-surface' : 'text-muted hover:bg-surface'}`}>{l}</button>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-1 text-sm">
        {crumbs.map((c, i) => <button key={i} onClick={() => setPath(path.slice(0, i))} className="text-accent hover:underline">{c}{i < crumbs.length - 1 ? ' /' : ''}</button>)}
      </div>
      <ErrorBox>{error}</ErrorBox>
      {!data ? <Loading /> : (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            {Array.isArray(data) && view === 'country' && <Table rows={data} cols={['name', 'people', 'teams', 'docs']} onPick={(r) => setPath([r.country])} />}
            {Array.isArray(data) && view === 'department' && <Table rows={data} cols={['department', 'people', 'teams', 'docs']} onPick={() => {}} />}
            {data.departments && <Table rows={data.departments} cols={['department', 'people', 'teams', 'docs']} onPick={(r) => setPath([path[0], r.department])} />}
            {data.teams && !data.worst_documents && <Table rows={data.teams} cols={['name', 'people', 'docs']} onPick={(r) => setPath([...path, r.team_id])} />}
            {data.worst_documents && (
              <Card className="space-y-3">
                <h3 className="font-semibold">{data.name}</h3>
                <p className="text-sm text-muted">{data.has_lead ? `Team lead: ${data.lead.name}` : 'This team has no team lead (an assumption we state openly).'}</p>
                <div className="flex flex-wrap gap-1.5">{Object.entries(data.sources).map(([s, n]) => <Chip key={s}>{s}: {n}</Chip>)}</div>
                <p className="text-xs font-semibold uppercase text-muted">Documents needing attention</p>
                <ul className="space-y-1 text-sm">{data.worst_documents.map((d) => <li key={d.doc_id} className="flex justify-between"><span>{d.title} <span className="text-muted">({d.source})</span></span><span className="tabular-nums">{d.trust}</span></li>)}</ul>
              </Card>
            )}
          </div>
          <Card>
            <h3 className="mb-2 font-semibold">Knowledge risks</h3>
            <p className="mb-2 text-xs text-muted">Topics with at most one active expert{path[0] ? ` in ${path[0]}` : ''}.</p>
            <ul className="space-y-2 text-sm">
              {risks.length === 0 && <li className="text-muted">None found.</li>}
              {risks.map((r) => <li key={r.topic_id}><b>{r.topic_name}</b>: {r.active_experts} active expert{r.active_experts === 1 ? ` (${r.only_expert.name})` : 's'}{r.experts_left ? `, ${r.experts_left} left` : ''}</li>)}
            </ul>
          </Card>
        </div>
      )}
    </div>
  )
}

function Table({ rows, cols, onPick }) {
  return (
    <Card className="overflow-x-auto p-0">
      <table className="w-full text-sm">
        <thead className="bg-soft text-left text-xs uppercase text-muted"><tr>{cols.map((c) => <th key={c} className="px-3 py-2">{c}</th>)}<th className="px-3 py-2">health</th></tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} onClick={() => onPick(r)} className="cursor-pointer border-t border-line hover:bg-soft">
              {cols.map((c) => <td key={c} className="px-3 py-2">{r[c]}</td>)}
              <td className="px-3 py-2"><HealthBar value={r.health} badge={r.badge} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  )
}
