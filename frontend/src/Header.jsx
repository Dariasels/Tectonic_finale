import { Logo } from './ui'

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
        {right}
      </div>
    </header>
  )
}

