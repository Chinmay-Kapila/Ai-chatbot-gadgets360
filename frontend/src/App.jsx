import { Cpu, Newspaper, Smartphone, Tv, Watch, Laptop } from 'lucide-react'
import ChatWidget from './components/ChatWidget'
import logo from './assets/logo.svg'

const CATEGORIES = [
  { icon: Smartphone, label: 'Mobiles' },
  { icon: Laptop, label: 'Laptops' },
  { icon: Tv, label: 'TVs' },
  { icon: Watch, label: 'Wearables' },
  { icon: Cpu, label: 'AI & Tech' },
  { icon: Newspaper, label: 'News' },
]

/**
 * Minimal host page standing in for a Gadgets360-style site, so the
 * floating assistant widget has real editorial context to sit on top of.
 */
function App() {
  return (
    <div className="min-h-screen bg-ink-50 dark:bg-ink-950">
      <header className="sticky top-0 z-40 border-b border-ink-100 bg-white/90 backdrop-blur dark:border-ink-800 dark:bg-ink-900/90">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2.5">
            <img src={logo} alt="" className="h-8 w-8 rounded-lg" />
            <span className="font-display text-lg font-bold text-ink-900 dark:text-white">
              Gadgets<span className="text-brand-500">360</span>
            </span>
          </div>
          <nav className="hidden gap-6 text-sm font-medium text-ink-600 dark:text-ink-300 sm:flex">
            {CATEGORIES.map(({ icon: Icon, label }) => (
              <a
                key={label}
                href="#"
                className="flex items-center gap-1.5 transition-colors hover:text-brand-500"
              >
                <Icon size={15} />
                {label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-5 py-16">
        <div className="max-w-2xl">
          <span className="font-mono text-xs uppercase tracking-widest text-brand-500">
            AI Assistant · Live
          </span>
          <h1 className="mt-3 font-display text-4xl font-bold leading-tight text-ink-900 dark:text-white sm:text-5xl">
            Ask anything about gadgets, tech news, and today&apos;s rates.
          </h1>
          <p className="mt-4 text-base leading-relaxed text-ink-500 dark:text-ink-400">
            Tap the assistant in the corner for phone recommendations, product
            comparisons, reviews or buying guides — all grounded in Gadgets360 data.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-6">
          {CATEGORIES.map(({ icon: Icon, label }) => (
            <div
              key={label}
              className="flex flex-col items-center gap-2 rounded-xl2 border border-ink-100 bg-white p-4 text-center shadow-sm dark:border-ink-800 dark:bg-ink-900"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-50 text-brand-500 dark:bg-brand-900/30">
                <Icon size={17} />
              </span>
              <span className="text-xs font-medium text-ink-600 dark:text-ink-300">
                {label}
              </span>
            </div>
          ))}
        </div>
      </main>

      <ChatWidget />
    </div>
  )
}

export default App
