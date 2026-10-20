import { Globe } from 'lucide-react'
import { LANGUAGES, useLang } from './i18n'
import { Logo } from './ui'

function LanguageSelect() {
  const { lang, setLang, t } = useLang()
  return (
    <label className="flex items-center gap-1 text-white">
      <Globe className="h-4 w-4" aria-hidden="true" /><span className="sr-only">{t('language')}</span>
      <select value={lang} onChange={(e) => setLang(e.target.value)} className="max-w-[7.5rem] rounded-lg border border-white/35 bg-[rgba(15,14,26,.45)] px-1.5 py-1.5 text-sm text-white">
        {LANGUAGES.map((l) => <option key={l.code} value={l.code} className="bg-white text-[#0F0E1A]">{l.name}</option>)}
      </select>
    </label>
  )
}

export function Header({ right }) {
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
        <div className="flex shrink-0 items-center gap-2"><LanguageSelect />{right}</div>
      </div>
    </header>
  )
}

