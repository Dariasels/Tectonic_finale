import { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Building2, Gauge, Search as SearchIcon, ShieldCheck, Upload as UploadIcon } from 'lucide-react'
import clsx from 'clsx'
import { api } from './api'
import { UserProvider, useUser } from './user'
import Search from './pages/Search'
import Approvals from './pages/Approvals'
import Upload from './pages/Upload'
import Org from './pages/Org'
import Model from './pages/Model'

function Shell() {
  const { users, user, setUser, error } = useUser()
  const [pending, setPending] = useState(0)

  useEffect(() => {
    if (!user) return
    api.approvals(user.person_id).then((a) => setPending(a.length)).catch(() => setPending(0))
  }, [user])

  const nav = [
    ['/', 'Search', SearchIcon], ['/approvals', 'Approvals', ShieldCheck], ['/upload', 'Add document', UploadIcon],
    ['/org', 'Organisation', Building2], ['/model', 'Model & scale', Gauge],
  ]
  const options = user && !users.some((u) => u.person_id === user.person_id) ? [user, ...users] : users

  return (
    <div className="min-h-screen">
      <header className="bg-linear-to-r from-sdw-yellow to-sdw-blue text-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
          <div>
            <h1 className="text-xl font-bold text-ink">Tectonic</h1>
            <p className="text-xs font-medium text-ink/80">Find it. Understand it. Trust it. Keep it trusted.</p>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <span className="hidden text-ink/80 sm:inline">Signed in as</span>
            <select value={user?.person_id ?? ''} onChange={(e) => setUser(options.find((u) => u.person_id === e.target.value))}
              className="max-w-64 rounded-lg border-0 bg-white/90 px-2 py-1.5 text-ink">
              {options.map((u) => <option key={u.person_id} value={u.person_id}>{u.label ?? `${u.name} (${u.role})`}</option>)}
            </select>
          </label>
        </div>
      </header>
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 md:flex-row">
        <nav className="flex gap-1 overflow-x-auto md:w-52 md:shrink-0 md:flex-col">
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => clsx('flex items-center gap-2 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium', isActive ? 'bg-white text-sdw-blue shadow-sm ring-1 ring-slate-200' : 'text-slate-600 hover:bg-white/70')}>
              <Icon className="h-4 w-4" />{label}
              {to === '/approvals' && pending > 0 && <span className="ml-auto rounded-full bg-sdw-yellow px-1.5 text-xs font-bold text-ink">{pending}</span>}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0 flex-1">
          {error && <div className="mb-3 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}
          {user ? (
            <Routes>
              <Route path="/" element={<Search />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/org" element={<Org />} />
              <Route path="/model" element={<Model />} />
            </Routes>
          ) : !error && <p className="text-sm text-slate-500">Starting the backend (about 10 seconds)...</p>}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return <BrowserRouter><UserProvider><Shell /></UserProvider></BrowserRouter>
}
