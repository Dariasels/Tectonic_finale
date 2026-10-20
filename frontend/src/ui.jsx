import clsx from 'clsx'
import { Check, Info, X } from 'lucide-react'

const BADGE = {
  green: 'bg-emerald-100 text-emerald-800 ring-emerald-300',
  yellow: 'bg-amber-100 text-amber-800 ring-amber-300',
  red: 'bg-rose-100 text-rose-800 ring-rose-300',
}
const BADGE_LABEL = { green: 'Reliable', yellow: 'Verify', red: 'Unreliable' }

export function TrustBadge({ badge, score, className }) {
  return (
    <span className={clsx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-sm font-semibold ring-1', BADGE[badge], className)}>
      <span className="text-base tabular-nums">{Math.round(score)}</span>
      <span className="text-xs font-medium opacity-80">{BADGE_LABEL[badge]}</span>
    </span>
  )
}

export const Chip = ({ children, className }) => (
  <span className={clsx('inline-flex items-center rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600', className)}>{children}</span>
)

export const Card = ({ children, className }) => (
  <div className={clsx('rounded-xl border border-slate-200 bg-white p-4 shadow-sm', className)}>{children}</div>
)

export const Button = ({ variant = 'primary', className, ...p }) => (
  <button
    {...p}
    className={clsx(
      'inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-50',
      variant === 'primary' && 'bg-sdw-blue text-white hover:bg-blue-800',
      variant === 'ghost' && 'bg-slate-100 text-slate-700 hover:bg-slate-200',
      variant === 'good' && 'bg-emerald-600 text-white hover:bg-emerald-700',
      variant === 'bad' && 'bg-rose-600 text-white hover:bg-rose-700',
      className,
    )}
  />
)

export const ErrorBox = ({ children }) => (children ? <div className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700 ring-1 ring-rose-200">{children}</div> : null)
export const Loading = ({ text = 'Loading...' }) => <div className="p-6 text-sm text-slate-500">{text}</div>

export function Reasons({ reasons }) {
  return (
    <ul className="space-y-1 text-sm">
      {reasons.map((r, i) => (
        <li key={i} className="flex items-start gap-2">
          {r.sign > 0 ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" /> : r.sign < 0 ? <X className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" /> : <Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />}
          <span>{r.text}</span>
        </li>
      ))}
    </ul>
  )
}

export function HealthBar({ value, badge }) {
  const color = badge === 'green' ? 'bg-emerald-500' : badge === 'yellow' ? 'bg-amber-400' : 'bg-rose-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded bg-slate-200"><div className={clsx('h-full', color)} style={{ width: `${value ?? 0}%` }} /></div>
      <span className="w-10 text-xs tabular-nums text-slate-600">{value ?? '-'}</span>
    </div>
  )
}
