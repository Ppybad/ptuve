import { useCallback, useEffect, useState } from 'react'
import { searchTidal, enqueueTidalDownload, getTidalLogin, getTidalStatus, type TidalItem, type TidalType } from '../api/tidal'
import { Search, Download as DownloadIcon, Disc, User } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function TidalSearch({ onQueued }: { onQueued?: () => void }) {
  const [query, setQuery] = useState('')
  const [type, setType] = useState<TidalType>('track')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<TidalItem[]>([])
  const [awaitingAuth, setAwaitingAuth] = useState(false)
  const [loginLink, setLoginLink] = useState<string | null>(null)
  const [loginCode, setLoginCode] = useState<string | null>(null)

  const doSearch = useCallback(async () => {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    try {
      const items = await searchTidal(q, type)
      setResults(items)
      setAwaitingAuth(false)
      setLoginLink(null)
      setLoginCode(null)
    } catch (e: any) {
      setResults([])
      const msg = e?.response?.data?.detail || 'No se pudo buscar en Tidal'
      if (String(msg).toLowerCase().includes('esperando autorización')) {
        setAwaitingAuth(true)
      }
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [query, type])

  const handleDownload = async (id: number) => {
    try {
      await enqueueTidalDownload(id, type === 'album' ? 'album' : 'track')
      toast.success('Añadido a la cola de descargas')
      onQueued?.()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || 'No se pudo encolar la descarga'
      toast.error(msg)
    }
  }

  useEffect(() => {
    if (!awaitingAuth) return
    const id = setInterval(async () => {
      try {
        const st = await getTidalStatus()
        if (st.status === 'connected') {
          setAwaitingAuth(false)
          setLoginLink(null)
          setLoginCode(null)
          toast.success('Tidal conectado')
        }
      } catch {}
    }, 5000)
    return () => clearInterval(id)
  }, [awaitingAuth])

  const makeAbsolute = (link?: string | null) => {
    if (!link) return null
    if (/^https?:\/\//i.test(link)) return link
    return `https://${link.replace(/^\/+/, '')}`
  }

  return (
    <div className="px-4 py-4">
      {awaitingAuth && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" />
          <div className="relative z-10 w-full max-w-md rounded-lg border border-slate-200 dark:border-gray-700 bg-white dark:bg-gray-950 p-5 shadow-lg">
            <div className="text-lg font-semibold mb-2 text-slate-900 dark:text-gray-100">Autorizar con Tidal</div>
            <div className="text-sm mb-4 text-slate-700 dark:text-gray-300">Necesitas autorizar el acceso. Abre el enlace de Tidal y pega el código si se solicita.</div>
            {loginCode && (
              <div className="mb-3">
                <div className="text-xs uppercase text-slate-500 dark:text-gray-400">Código de verificación</div>
                <div className="mt-1 text-center text-3xl tracking-widest font-mono select-all text-slate-900 dark:text-gray-100">{loginCode}</div>
              </div>
            )}
            <div className="flex items-center gap-2">
              {!loginLink ? (
                <button
                  onClick={async () => {
                    try {
                      const info = await getTidalLogin()
                      const abs = makeAbsolute(info.link || null)
                      setLoginLink(abs)
                      setLoginCode(info.code || null)
                      if (abs) window.open(abs, '_blank', 'noopener,noreferrer')
                    } catch {
                      toast.error('No se pudo obtener el link de login')
                    }
                  }}
                  className="px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-500"
                >
                  Obtener Link de Login
                </button>
              ) : (
                <a
                  href={loginLink || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-500"
                >
                  Abrir enlace de Tidal
                </a>
              )}
              <button
                onClick={async () => {
                  try {
                    const st = await getTidalStatus()
                    if (st.status === 'connected') {
                      setAwaitingAuth(false)
                      setLoginLink(null)
                      setLoginCode(null)
                      toast.success('Tidal conectado')
                    } else {
                      toast('Sigue pendiente de autorización')
                    }
                  } catch {
                    toast.error('No se pudo verificar el estado')
                  }
                }}
                className="px-3 py-2 rounded-md border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800"
              >
                Verificar Estado
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="flex items-center gap-2 mb-4">
        <div className="relative flex-1">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar en Tidal…"
            className="w-full rounded-md bg-white border border-slate-300 text-slate-900 placeholder-slate-500 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-400 px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
            onKeyDown={(e) => {
              if (e.key === 'Enter') doSearch()
            }}
          />
          <Search size={18} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 dark:text-gray-500" />
        </div>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as TidalType)}
          className="rounded-md bg-white border border-slate-300 text-slate-900 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 px-3 py-2 transition-colors"
        >
          <option value="track">Tracks</option>
          <option value="album">Albums</option>
          <option value="artist">Artists</option>
        </select>
        <button
          onClick={doSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-500 disabled:bg-slate-300 dark:disabled:bg-gray-700 transition-colors"
        >
          Buscar
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {results.map((item) => (
          <div
            key={`${type}-${item.id}`}
            className="rounded-lg border border-slate-200 dark:border-gray-700 bg-white dark:bg-gray-950 shadow-sm dark:shadow-none overflow-hidden transition-colors"
          >
            <div className="aspect-square bg-slate-100 dark:bg-gray-900 flex items-center justify-center">
              {item.image ? (
                <img
                  src={item.image}
                  alt={item.title}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
              ) : (
                <Disc className="text-slate-400 dark:text-gray-600" size={48} />
              )}
            </div>
            <div className="p-3">
              <div className="font-medium text-slate-900 dark:text-gray-100 truncate">{item.title}</div>
              <div className="text-sm text-slate-600 dark:text-gray-400 flex items-center gap-1 truncate">
                <User size={14} />
                <span>{item.artist || '—'}</span>
              </div>
              {item.album_name && (
                <div className="text-xs text-slate-500 dark:text-gray-500 truncate">{item.album_name}</div>
              )}
              <div className="mt-3">
                <button
                  onClick={() => handleDownload(item.id)}
                  className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800 text-sm transition-colors"
                  title="Descargar"
                >
                  <DownloadIcon size={16} />
                  Descargar
                </button>
              </div>
            </div>
          </div>
        ))}
        {!loading && results.length === 0 && (
          <div className="text-sm text-slate-600 dark:text-gray-400 col-span-full">No hay resultados</div>
        )}
      </div>
    </div>
  )
}
