import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

export default function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const isDark = theme === 'dark'
  return (
    <button
      onClick={toggle}
      title={isDark ? 'Cambiar a Light' : 'Cambiar a Dark'}
      className="inline-flex items-center justify-center w-9 h-9 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800 transition-colors"
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  )
}
