import clsx from 'clsx'
import { BookOpen, Check, Cloud, FileText, GitBranch, HardDrive, Info, MessageSquare, X } from 'lucide-react'

const DOT = { green: 'bg-ok', yellow: 'bg-warn', red: 'bg-bad' }
const BADGE_LABEL = { green: 'Reliable', yellow: 'Verify', red: 'Unreliable' }

/* Status is shown as a dot; brand colours are never used for status. */
export function TrustBadge({ badge, score, className }) {
  return (
    <span className={clsx('inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-sm', className)} title={BADGE_LABEL[badge]}>
      <span className={clsx('h-2.5 w-2.5 rounded-full', DOT[badge])} aria-hidden="true" />
      <span className="text-base font-extrabold tabular-nums">{Math.round(score)}</span>
      <span className="text-xs font-medium text-muted">{BADGE_LABEL[badge]}</span>
    </span>
  )
}

export const Chip = ({ children, className }) => (
  <span className={clsx('inline-flex items-center rounded-md bg-soft px-2 py-0.5 text-xs text-muted', className)}>{children}</span>
)

export const Card = ({ children, className }) => (
  <div className={clsx('rounded-xl border border-line bg-surface p-4', className)}>{children}</div>
)

export const Button = ({ variant = 'primary', className, ...p }) => (
  <button
    {...p}
    className={clsx(
      'inline-flex items-center justify-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition disabled:opacity-50',
      variant === 'primary' && 'bg-[linear-gradient(100deg,#F0343C,#B3308F_60%,#7B2FBE)] text-white hover:opacity-90',
      variant === 'ghost' && 'bg-soft text-main hover:bg-line',
      variant === 'good' && 'bg-oksolid text-white hover:opacity-90',
      variant === 'bad' && 'bg-badsolid text-white hover:opacity-90',
      className,
    )}
  />
)

export const ErrorBox = ({ children }) => (children ? <div className="rounded-lg bg-badbg p-3 text-sm text-badtext ring-1 ring-bad/30">{children}</div> : null)
export const Loading = ({ text = 'Loading...' }) => <div className="p-6 text-sm text-muted">{text}</div>

export function Reasons({ reasons }) {
  return (
    <ul className="space-y-1 text-sm">
      {reasons.map((r, i) => (
        <li key={i} className="flex items-start gap-2">
          {r.sign > 0 ? <Check className="mt-0.5 h-4 w-4 shrink-0 text-oktext" /> : r.sign < 0 ? <X className="mt-0.5 h-4 w-4 shrink-0 text-badtext" /> : <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted" />}
          <span>{r.text}</span>
        </li>
      ))}
    </ul>
  )
}

export function HealthBar({ value, badge }) {
  const color = badge === 'green' ? 'bg-ok' : badge === 'yellow' ? 'bg-warn' : 'bg-bad'
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-24 overflow-hidden rounded bg-line"><div className={clsx('h-full', color)} style={{ width: `${value ?? 0}%` }} /></div>
      <span className="w-10 text-xs tabular-nums text-muted">{value ?? '-'}</span>
    </div>
  )
}

const SRC_ICON = { SharePoint: FileText, Teams: MessageSquare, OneDrive: Cloud, Notion: BookOpen, GitHub: GitBranch, 'Legacy drive': HardDrive }
export function SourceChip({ source }) {
  const Icon = SRC_ICON[source] ?? FileText
  return <Chip className="gap-1"><Icon className="h-3 w-3" />{source}</Chip>
}

/* Graphlas logo, inline (46x46) */
export function Logo({ size = 46 }) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      <defs><radialGradient id="c" cx="35%" cy="30%"><stop offset="0" stopColor="#FF8B4A" /><stop offset="1" stopColor="#7B2FBE" /></radialGradient></defs>
      <path d="M78 22 A42 42 0 1 0 82 80" fill="none" stroke="#17104A" strokeWidth="8" strokeLinecap="round" />
      <path d="M52 52 H90" stroke="#17104A" strokeWidth="5" strokeLinecap="round" /><circle cx="92" cy="52" r="6" fill="#17104A" />
      <g stroke="#B3308F" strokeWidth="3.5" strokeLinecap="round">
        <line x1="50" y1="52" x2="70" y2="26" /><line x1="50" y1="52" x2="28" y2="76" />
        <line x1="50" y1="52" x2="68" y2="80" /><line x1="50" y1="52" x2="22" y2="46" />
      </g>
      <circle cx="70" cy="26" r="7" fill="#D63384" /><circle cx="28" cy="76" r="7" fill="#3A1470" />
      <circle cx="68" cy="80" r="7" fill="#9B30E8" /><circle cx="22" cy="46" r="7" fill="#FF8B4A" />
      <circle cx="50" cy="52" r="10" fill="url(#c)" />
    </svg>
  )
}
