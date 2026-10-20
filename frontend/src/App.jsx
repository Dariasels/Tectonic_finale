import { useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import { Building2, Gauge, Plug, Radio, Search as SearchIcon, ShieldCheck } from 'lucide-react'
import clsx from 'clsx'
import { api } from './api'
import { UserProvider, useUser } from './user'
import { Header } from './Header'
import Login from './pages/Login'
import Tools from './pages/Tools'
import Capture from './pages/Capture'
import Splash from './pages/Splash'
import { getBg, setBg } from './theme'
import { I18nProvider, useT } from './i18n'
import Search from './pages/Search'
import Approvals from './pages/Approvals'
import Org from './pages/Org'
import Model from './pages/Model'

function Closed() {
  return (
    <div className="rounded-xl border border-line bg-surface p-4 text-sm">
      <h2 className="text-[26px] font-extrabold">Not available for your role</h2>
      <p className="mt-1 text-muted">This page is for technically authorised people and executives: the system admin, the CEO, country leads and department heads. Switch to one of them in the menu at the top.</p>
    </div>
  )
}

function Shell({ signOut }) {
  const t = useT()
  const { users, user, setUser, error } = useUser()
  const [pending, setPending] = useState(0)
  const [technical, setTechnical] = useState(false)       // system admin, executives and higher management only
  const [bg, setBgState] = useState(getBg())
  const pickBg = (v) => { setBg(v); setBgState(v) }

  useEffect(() => {
    if (!user) return
    api.approvals(user.person_id).then((a) => setPending(a.length)).catch(() => setPending(0))
    api.access(user.person_id).then((a) => setTechnical(a.can_view_technical)).catch(() => setTechnical(false))
  }, [user])

  const nav = [
    ['/', 'nav_search', SearchIcon], ['/approvals', 'nav_approvals', ShieldCheck], ['/tools', 'nav_tools', Plug],
    ['/org', 'nav_org', Building2],
    ...(technical ? [['/capture', 'nav_capture', Radio], ['/model', 'nav_model', Gauge]] : []),
  ]
  const options = user && !users.some((u) => u.person_id === user.person_id) ? [user, ...users] : users

  return (
    <div className="min-h-screen">
      <Header right={
        <div className="flex shrink-0 items-center gap-2 text-sm">
          <div className="flex items-center gap-2" role="group" aria-label="Page background">
            <span className="hidden text-xs font-medium text-white min-[900px]:inline">{t('background')}</span>
            {[['white', 'White', '#ffffff'], ['pink', 'Light pink', '#f9d5e2'], ['dark', 'Dark', '#1a1830']].map(([k, label, c]) => (
              <button key={k} aria-label={`${label} background`} title={`${label} background`} aria-pressed={bg === k} onClick={() => pickBg(k)}
                className={`flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs font-bold ${k === 'dark' ? 'text-white' : 'text-[#17104A]'} ${bg === k ? 'border-white ring-2 ring-[#0F0E1A]/70' : 'border-white/50'}`} style={{ background: c }}>
                {bg === k ? '✓' : ''}
              </button>
            ))}
          </div>
          <label>
            <span className="sr-only">Signed in as</span>
            <select value={user?.person_id ?? ''} onChange={(e) => setUser(options.find((u) => u.person_id === e.target.value))}
              className="max-w-[7.5rem] rounded-lg border border-white/35 bg-[rgba(15,14,26,.45)] px-2 py-1.5 text-white min-[720px]:max-w-72">
              {options.map((u) => <option key={u.person_id} value={u.person_id} className="bg-white text-[#0F0E1A]">{u.label ?? `${u.name} (${u.role})`}</option>)}
            </select>
          </label>
          <button onClick={signOut} className="hidden rounded-lg border border-white/35 bg-[rgba(15,14,26,.45)] px-2 py-1.5 text-white min-[720px]:block">{t('sign_out')}</button>
        </div>} />
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 min-[720px]:flex-row">
        <nav className="flex gap-1 overflow-x-auto min-[720px]:w-52 min-[720px]:shrink-0 min-[720px]:flex-col" aria-label="Main">
          {nav.map(([to, key, Icon]) => (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => clsx(
              'flex items-center gap-2 whitespace-nowrap rounded-lg border-l-[3px] px-3 py-2 text-sm font-medium',
              isActive ? 'border-magenta bg-surface text-main' : 'border-transparent text-muted hover:bg-surface')}>
              <Icon className="h-4 w-4" />{t(key)}
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
              <Route path="/capture" element={technical ? <Capture /> : <Closed />} />
              <Route path="/tools" element={<Tools />} />
              <Route path="/org" element={<Org />} />
              <Route path="/model" element={technical ? <Model /> : <Closed />} />
            </Routes>
          ) : !error && <p className="text-sm text-muted">Starting the backend (about 10 seconds)...</p>}
        </main>
      </div>
    </div>
  )
}

const getFlag = () => {
  try {
    if (new URLSearchParams(window.location.search).has('demo')) localStorage.setItem('graphlas_signed_in', '1')   // ?demo skips the login (used for demos and checks)
    return localStorage.getItem('graphlas_signed_in') === '1'
  } catch { return false }
}
const setFlag = (v) => { try { v ? localStorage.setItem('graphlas_signed_in', '1') : localStorage.removeItem('graphlas_signed_in') } catch { /* private mode */ } }

const splashSeen = () => {
  try {
    const q = new URLSearchParams(window.location.search)
    if (q.has('demo') || q.has('nosplash')) sessionStorage.setItem('graphlas_splash', '1')
    return sessionStorage.getItem('graphlas_splash') === '1'
  } catch { return false }
}

function Gate() {
  const [splash, setSplash] = useState(!splashSeen())
  const [startMode, setStartMode] = useState(null)       // which tab of the login to open: 'signin' or 'create'
  const [signedIn, setSignedIn] = useState(getFlag())
  const { setUser } = useUser()
  const finish = (person) => { setUser(person); setFlag(true); setSignedIn(true) }
  const signOut = () => { setFlag(false); setSignedIn(false) }
  const leaveSplash = (mode) => { try { sessionStorage.setItem('graphlas_splash', '1') } catch { /* private mode */ } setStartMode(mode); setSplash(false) }
  if (splash) return <Splash onDone={leaveSplash} />
  return signedIn ? <Shell signOut={signOut} /> : <Login onDone={finish} initialMode={startMode} />
}

export default function App() {
  return <BrowserRouter><I18nProvider><UserProvider><Gate /></UserProvider></I18nProvider></BrowserRouter>
}
