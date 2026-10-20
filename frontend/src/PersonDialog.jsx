import { useEffect, useRef, useState } from 'react'
import { Copy, Mail, X } from 'lucide-react'
import { api, errText } from './api'
import { useT } from './i18n'
import { Button } from './ui'

/* Contact card of a colleague: opened by clicking a name. */
export default function PersonDialog({ personId, userId, onClose }) {
  const t = useT()
  const [p, setP] = useState(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    api.contact(personId, userId).then(setP).catch((e) => setError(errText(e)))
    const esc = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [personId, userId, onClose])
  useEffect(() => { ref.current?.focus() }, [p])

  const copy = async () => {
    try { await navigator.clipboard.writeText(p.email); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* clipboard blocked */ }
  }
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal="true" aria-label="Contact details" onClick={onClose}>
      <div className="w-full max-w-sm space-y-3 rounded-xl border border-line bg-surface p-5 text-main" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-xl font-extrabold">{p?.name ?? 'Contact'}</h2>
            {p && <p className="text-sm text-muted">{p.role}</p>}
          </div>
          <button ref={ref} onClick={onClose} aria-label="Close" className="rounded-lg p-1 hover:bg-soft"><X className="h-5 w-5" /></button>
        </div>
        {error && <p className="text-sm text-badtext">{error}</p>}
        {!p && !error && <p className="text-sm text-muted">Loading...</p>}
        {p && (
          <>
            <dl className="space-y-1 text-sm">
              <div className="flex gap-2"><dt className="w-20 shrink-0 text-muted">Team</dt><dd>{p.team}</dd></div>
              <div className="flex gap-2"><dt className="w-20 shrink-0 text-muted">Department</dt><dd>{p.department}</dd></div>
              <div className="flex gap-2"><dt className="w-20 shrink-0 text-muted">Country</dt><dd>{p.country}</dd></div>
              {p.manager && <div className="flex gap-2"><dt className="w-20 shrink-0 text-muted">Manager</dt><dd>{p.manager.name}, {p.manager.role}</dd></div>}
              {p.moved_from && <div className="flex gap-2"><dt className="w-20 shrink-0 text-muted">Moved from</dt><dd>{p.moved_from}</dd></div>}
            </dl>
            {p.email ? (
              <div className="space-y-2 rounded-lg bg-soft p-3">
                <p className="break-all text-sm font-medium">{p.email}</p>
                <div className="flex gap-2">
                  <a href={`mailto:${p.email}`} className="inline-flex items-center gap-1.5 rounded-lg bg-[linear-gradient(100deg,#F0343C,#B3308F_60%,#7B2FBE)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90"><Mail className="h-4 w-4" />{t('send_email')}</a>
                  <Button variant="ghost" onClick={copy}><Copy className="h-4 w-4" />{copied ? '✓' : t('copy')}</Button>
                </div>
              </div>
            ) : <p className="rounded-lg bg-warnbg p-3 text-sm text-warntext">{p.note}</p>}
            {p.email && <p className="text-xs text-muted">{p.note}</p>}
          </>
        )}
      </div>
    </div>
  )
}
