import { LogIn, UserPlus } from 'lucide-react'
import { useT } from '../i18n'
import { Logo } from '../ui'

/* First page: the logo, Sign in and Create a new login. */
export default function Splash({ onDone }) {
  const t = useT()
  return (
    <div
      className="flex min-h-screen items-center justify-center px-6 text-[#17104A]"
      style={{
        background:
          'radial-gradient(circle at 0% 100%, rgba(179,48,143,.9) 0%, rgba(179,48,143,0) 55%), linear-gradient(to bottom left, #0F0E1A 0%, #2A1458 10%, #B3308F 30%, #F0343C 52%, #FF8B4A 88%)',
      }}
    >
      <div className="flex w-full max-w-4xl flex-col items-center">
        <div className="flex items-center justify-center gap-[2vw]">
          <div className="shrink-0" style={{ width: 'clamp(64px, 11vw, 150px)' }}>
            <Logo size="100%" />
          </div>
          <h1 className="flex items-center gap-[1.5vw] leading-none" style={{ fontSize: 'clamp(40px, 9.5vw, 120px)' }}>
            <span><span className="font-extrabold">Graph</span><span className="font-light">las</span></span>
            <span className="rounded-full px-[0.28em] py-[0.08em] font-extrabold text-white"
              style={{ fontSize: '0.36em', background: 'linear-gradient(90deg,#FF8B4A,#B3308F,#2A1458)' }}>2.0</span>
          </h1>
        </div>
        <div className="mt-[2.2vw] flex w-[78%] items-center gap-3" aria-hidden="true">
          <span className="h-[2px] flex-1" style={{ background: 'linear-gradient(90deg,#FF8B4A,#B3308F,#17104A)' }} />
          <span className="h-3 w-3 rounded-full" style={{ background: 'radial-gradient(circle at 35% 30%,#FF8B4A,#7B2FBE)' }} />
          <span className="h-[2px] flex-1" style={{ background: 'linear-gradient(90deg,#B3308F,#17104A)' }} />
        </div>
        <p className="mt-[1.6vw] text-center font-medium uppercase" style={{ fontSize: 'clamp(11px, 1.6vw, 20px)', letterSpacing: '0.45em', paddingLeft: '0.45em' }}>An improved solution</p>
        <p className="mt-[2vw] text-center font-medium" style={{ fontSize: 'clamp(15px, 2.6vw, 34px)' }}>
          Connect the dots.{' '}
          <span className="font-extrabold text-white">Unlock what matters.</span>
        </p>

        <div className="mt-[3vw] flex flex-wrap items-center justify-center gap-3">
          <button onClick={() => onDone('signin')} autoFocus
            className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-base font-bold text-[#17104A] hover:bg-white/90">
            <LogIn className="h-5 w-5" />{t('sign_in')}
          </button>
          <button onClick={() => onDone('create')}
            className="inline-flex items-center gap-2 rounded-lg border-2 border-white px-6 py-3 text-base font-bold text-white hover:bg-white/15">
            <UserPlus className="h-5 w-5" />{t('create_login')}
          </button>
        </div>

      </div>
    </div>
  )
}
