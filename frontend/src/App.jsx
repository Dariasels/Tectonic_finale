import { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Building2, Gauge, Search as SearchIcon, ShieldCheck, Upload as UploadIcon } from 'lucide-react'
import clsx from 'clsx'
import { api } from './api'
import { UserProvider, useUser } from './user'
import { Logo } from './ui'
import Search from './pages/Search'
import Approvals from './pages/Approvals'
import Upload from './pages/Upload'
import Org from './pages/Org'
import Model from './pages/Model'

function Header({ options, user, setUser }) {
  return (
    <header
      className="sticky top-0 z-50 text-white"
      style={{
        background: 'linear-gradient(100deg, #FF8B4A 0%, #F0343C 32%, #B3308F 58%, #2A1458 82%, #0F0E1A 100%)',
        paddingTop: 'env(safe-area-inset-top, 0px)',
        minHeight: 'calc(76px + env(safe-area-inset-top, 0px))',
      }}
    >
      <div className="mx-auto flex h-[76px] max-w-6xl items-center justify-between gap-2 px-3 min-[720px]:gap-3 min-[720px]:px-4">
        <div className="flex min-w-0 items-center gap-3">
          <Logo size={40} />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-[20px] leading-none text-[#17104A] min-[720px]:text-[30px]">
                <span className="font-extrabold">Graph</span><span className="font-light">las</span>
              </h1>
              <span className="rounded-full bg-[linear-gradient(90deg,#FF8B4A,#B3308F,#2A1458)] px-2 py-0.5 text-xs font-extrabold text-white min-[720px]:px-2.5 min-[720px]:text-sm">2.0</span>
            </div>
            <p className="mt-1 hidden text-xs font-medium min-[720px]:block">
              <span className="text-[#17104A]">Connect the dots. </span><span className="font-extrabold text-white">Unlock what matters.</span>
            </p>
          </div>
        </div>
        <label className="flex shrink-0 items-center gap-2 text-sm">
          <span className="sr-only">Signed in as</span>
          <select
            value={user?.person_id ?? ''}
            onChange={(e) => setUser(options.find((u) => u.person_id === e.target.value))}
            className="max-w-[7.5rem] rounded-lg border border-white/35 bg-[rgba(15,14,26,.45)] px-2 py-1.5 text-white min-[720px]:max-w-72"
          >
            {options.map((u) => <option key={u.person_id} value={u.person_id} className="bg-white text-[#0F0E1A]">{u.label ?? `${u.name} (${u.role})`}</option>)}
          </select>
        </label>
      </div>
    </header>
  )
}

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
      <Header options={options} user={user} setUser={setUser} />
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 min-[720px]:flex-row">
        <nav className="flex gap-1 overflow-x-auto min-[720px]:w-52 min-[720px]:shrink-0 min-[720px]:flex-col" aria-label="Main">
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => clsx(
              'flex items-center gap-2 whitespace-nowrap rounded-lg border-l-[3px] px-3 py-2 text-sm font-medium',
              isActive ? 'border-magenta bg-surface text-main' : 'border-transparent text-muted hover:bg-surface')}>
              <Icon className="h-4 w-4" />{label}
              {to === '/approvals' && pending > 0 && <span className="ml-auto rounded-full bg-badsolid px-1.5 text-xs font-bold text-white">{pending}</span>}
            </NavLink>
          ))}
        </nav>
        <main className="min-w-0 flex-1">
          {error && <div className="mb-3 rounded-lg bg-badbg p-3 text-sm text-badtext">{error}</div>}
          {user ? (
            <Routes>
              <Route path="/" element={<Search />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/org" element={<Org />} />
              <Route path="/model" element={<Model />} />
            </Routes>
          ) : !error && <p className="text-sm text-muted">Starting the backend (about 10 seconds)...</p>}
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return <BrowserRouter><UserProvider><Shell /></UserProvider></BrowserRouter>
}
