import { X } from 'lucide-react'
import logo from '../assets/logo.svg'
import ThemeToggle from './ThemeToggle'

/**
 * Header bar for the chat panel: brand mark, title, live-status dot,
 * theme toggle, and close button.
 */
function Header({ onClose, isDark, onToggleTheme }) {
  return (
    <div className="flex items-center justify-between bg-brand-500 px-4 py-3">
      <div className="flex items-center gap-2.5">
        <img src={logo} alt="" className="h-8 w-8 rounded-lg" />
        <div className="flex flex-col leading-tight">
          <span className="font-display text-sm font-bold text-white">
            Gadgets360 AI Assistant
          </span>
          <span className="flex items-center gap-1 text-[0.68rem] text-white/80">
            <span className="h-1.5 w-1.5 rounded-full bg-signal-green" />
            Online
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <ThemeToggle isDark={isDark} onToggle={onToggleTheme} />
        <button
          type="button"
          onClick={onClose}
          aria-label="Close chat"
          className="flex h-8 w-8 items-center justify-center rounded-full text-white/90 transition-colors hover:bg-white/15"
        >
          <X size={17} />
        </button>
      </div>
    </div>
  )
}

export default Header
