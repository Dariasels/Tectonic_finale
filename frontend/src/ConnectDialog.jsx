import { useEffect, useRef } from 'react'
import { Check, X } from 'lucide-react'
import { Button } from './ui'

/* Simulated consent screen. In production the provider's own OAuth page is shown instead. */
export default function ConnectDialog({ provider, onAllow, onCancel }) {
  const ref = useRef(null)
  useEffect(() => {
    ref.current?.focus()
    const esc = (e) => e.key === 'Escape' && onCancel()
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onCancel])
  if (!provider) return null
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4" role="dialog" aria-modal="true" aria-labelledby="cd-title" onClick={(e) => { e.stopPropagation(); onCancel() }}>
      <div className="w-full max-w-md space-y-4 rounded-xl border border-line bg-surface p-5 text-main" onClick={(e) => e.stopPropagation()}>
        <div>
          <h2 id="cd-title" className="text-xl font-extrabold">Connect {provider.label}</h2>
          <p className="text-xs text-muted">Demo: this screen is simulated, nothing leaves this computer.</p>
        </div>
        <div>
          <p className="mb-1 text-sm font-semibold">Graphlas will read</p>
          <ul className="space-y-1 text-sm">{provider.reads.map((r) => <li key={r} className="flex gap-2"><Check className="mt-0.5 h-4 w-4 shrink-0 text-oktext" />{r}</li>)}</ul>
        </div>
        <div>
          <p className="mb-1 text-sm font-semibold">Graphlas will never read</p>
          <ul className="space-y-1 text-sm">{provider.never.map((r) => <li key={r} className="flex gap-2"><X className="mt-0.5 h-4 w-4 shrink-0 text-badtext" />{r}</li>)}</ul>
        </div>
        <p className="text-xs text-muted">Only links and metadata are kept. You can disconnect at any time under Connected tools.</p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onCancel}>Cancel</Button>
          <button ref={ref} onClick={onAllow} className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-[linear-gradient(100deg,#F0343C,#B3308F_60%,#7B2FBE)] px-3 py-1.5 text-sm font-medium text-white hover:opacity-90">Allow</button>
        </div>
      </div>
    </div>
  )
}
