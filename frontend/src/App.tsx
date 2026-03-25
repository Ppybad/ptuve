import { useCallback, useEffect, useMemo, useState } from 'react'
import DownloadForm from './components/DownloadForm'
import DownloadTable from './components/DownloadTable'
import { deleteDownload, fetchDownloads, retryDownload } from './api/downloads'
import type { DownloadTask } from './types'
import { toast } from 'react-hot-toast'
import ThemeToggle from './components/ThemeToggle'

export default function App() {
  const [items, setItems] = useState<DownloadTask[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(10)
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<'ALL' | 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'>('ALL')

  const load = useCallback(async (s = skip, l = limit, q = search, st = status) => {
    setLoading(true)
    try {
      const data = await fetchDownloads(s, l, q, st === 'ALL' ? undefined : st)
      setItems(data.items)
      setTotal(data.total)
      setSkip(data.skip)
      setLimit(data.limit)
    } finally {
      setLoading(false)
    }
  }, [skip, limit, search, status])

  useEffect(() => {
    load(0, limit, search, status)
  }, [limit, load])

  const hasInProgress = useMemo(
    () => items.some((t) => t.status === 'PENDING' || t.status === 'PROCESSING'),
    [items],
  )

  useEffect(() => {
    if (!hasInProgress) return
    const id = setInterval(() => load(skip, limit), 3000)
    return () => clearInterval(id)
  }, [hasInProgress, load, skip, limit])

  const handleCreated = useCallback(async () => {
    await load(0, limit, search, status)
  }, [load, limit, search, status])

  const handleRetry = useCallback(async (id: string) => {
    try {
      await retryDownload(id)
      toast.success('Reintento encolado')
      await load(skip, limit, search, status)
    } catch {
      toast.error('No se pudo reintentar')
    }
  }, [load, skip, limit, search, status])

  const handleDelete = useCallback(async (id: string) => {
    try {
      await deleteDownload(id)
      toast.success('Tarea eliminada')
      await load(skip, limit, search, status)
    } catch {
      toast.error('No se pudo eliminar')
    }
  }, [load, skip, limit, search, status])

  const currentPage = Math.floor(skip / limit) + 1
  const totalPages = Math.max(1, Math.ceil(total / limit))
  const pageNumbers = (() => {
    const pages: number[] = []
    const windowSize = 5
    const start = Math.max(1, currentPage - Math.floor(windowSize / 2))
    const end = Math.min(totalPages, start + windowSize - 1)
    const realStart = Math.max(1, end - windowSize + 1)
    for (let p = realStart; p <= end; p++) pages.push(p)
    return pages
  })()

  useEffect(() => {
    const h = setTimeout(() => {
      load(0, limit, search, status)
    }, 400)
    return () => clearTimeout(h)
  }, [search, status])

  return (
    <div className="min-h-full">
      <header className="border-b border-slate-200 dark:border-gray-800 bg-white/80 dark:bg-gray-950/80 backdrop-blur">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900 dark:text-gray-100">Descargas</h1>
            <p className="text-sm text-slate-500 dark:text-gray-400">Pegá la URL para iniciar una nueva descarga</p>
          </div>
          <ThemeToggle />
        </div>
      </header>
      <main className="max-w-5xl mx-auto">
        <DownloadForm onCreated={handleCreated} />
        <div className="flex items-center justify-between px-4 pb-2 flex-wrap gap-2">
          <div className="text-sm text-slate-600 dark:text-gray-400">{total} tareas</div>
          <div className="flex items-center gap-2">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por título o URL…"
              className="bg-white border border-slate-300 text-slate-900 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 rounded px-3 py-1.5 text-sm w-64"
            />
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value as any)}
              className="bg-white border border-slate-300 text-slate-900 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 rounded px-2 py-1 text-sm"
            >
              <option value="ALL">Todos</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="COMPLETED">Completed</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-white border border-slate-300 text-slate-900 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 rounded px-2 py-1 text-sm"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
            <button
              onClick={() => load(skip, limit)}
              disabled={loading}
              className="px-3 py-1.5 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800 text-sm"
            >
              Refrescar
            </button>
          </div>
        </div>
        <DownloadTable items={items} onRetry={handleRetry} onDelete={handleDelete} />
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between flex-wrap gap-2">
          <div className="text-sm text-slate-600 dark:text-gray-400">
            Mostrando {Math.min(skip + items.length, total)} de {total} resultados
          </div>
          <ul className="flex items-center gap-1">
            {currentPage > 3 && (
              <>
                <li>
                  <button
                    className="px-2 py-1 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800 text-sm"
                    onClick={() => load(0, limit, search, status)}
                  >
                    1
                  </button>
                </li>
                <li className="text-slate-400 dark:text-gray-500 px-1">…</li>
              </>
            )}
            {pageNumbers.map((p) => (
              <li key={p}>
                <button
                  className={`px-2 py-1 rounded border text-sm ${
                    p === currentPage
                      ? 'bg-slate-100 dark:bg-gray-800 border-slate-300 dark:border-gray-600'
                      : 'border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800'
                  }`}
                  onClick={() => load((p - 1) * limit, limit, search, status)}
                >
                  {p}
                </button>
              </li>
            ))}
            {currentPage < totalPages - 2 && (
              <>
                <li className="text-slate-400 dark:text-gray-500 px-1">…</li>
                <li>
                  <button
                    className="px-2 py-1 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800 text-sm"
                    onClick={() => load((totalPages - 1) * limit, limit, search, status)}
                  >
                    {totalPages}
                  </button>
                </li>
              </>
            )}
          </ul>
        </div>
      </main>
    </div>
  )
}
