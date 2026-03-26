import { Download, RotateCw, Trash2 } from 'lucide-react'
import type { DownloadTask } from '../types'
import { getDownloadFileUrl } from '../api/downloads'

interface Props {
  items: DownloadTask[]
  onRetry: (id: string) => void
  onDelete: (id: string) => void
}

function StatusBadge({ status }: { status: DownloadTask['status'] }) {
  const color =
    status === 'PENDING'
      ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-700'
      : status === 'PROCESSING'
      ? 'bg-yellow-50 text-yellow-700 border-yellow-200 dark:bg-yellow-900/40 dark:text-yellow-300 dark:border-yellow-700'
      : status === 'COMPLETED'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-700'
      : 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-700'
  return <span className={`px-2 py-1 rounded text-xs border ${color}`}>{status}</span>
}

export default function DownloadTable({ items, onRetry, onDelete }: Props) {
  return (
    <div className="max-w-5xl mx-auto p-4">
      <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-gray-800">
        <table className="w-full text-sm min-w-[720px]">
          <thead className="bg-slate-50 text-slate-600 dark:bg-gray-900 dark:text-gray-300 uppercase text-xs">
            <tr>
              <th className="text-left px-4 py-3">Título / Álbum</th>
              <th className="text-left px-4 py-3">Estado</th>
              <th className="text-left px-4 py-3 w-40">Acciones</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-gray-800">
            {items.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50 dark:hover:bg-gray-900/60">
                <td className="px-4 py-3">
                  <div className="text-slate-900 dark:text-gray-100 truncate max-w-[600px]">
                    {(t.title || t.url).split(' — ')[0]}
                  </div>
                  {(() => {
                    const parts = (t.title || '').split(' — ')
                    if (parts.length >= 2) {
                      const album = parts[1]
                      const artist = parts[2]
                      return (
                        <div className="text-xs text-slate-500 dark:text-gray-400">
                          {album && <span className="mr-2">Álbum: {album}</span>}
                          {artist && <span>Artista: {artist}</span>}
                        </div>
                      )
                    }
                    return (
                      <div className="text-xs text-slate-500 dark:text-gray-400">
                        {new Date(t.created_at).toLocaleString()}
                      </div>
                    )
                  })()}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={t.status} />
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {t.status === 'COMPLETED' && (
                      <a
                        href={getDownloadFileUrl(t.id)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800"
                        title="Descargar archivo"
                      >
                        <Download size={16} />
                      </a>
                    )}
                    {t.status === 'FAILED' && (
                      <button
                        onClick={() => onRetry(t.id)}
                        className="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800"
                        title="Reintentar"
                      >
                        <RotateCw size={16} />
                      </button>
                    )}
                    <button
                      onClick={() => onDelete(t.id)}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded border border-slate-300 dark:border-gray-700 hover:bg-slate-100 dark:hover:bg-gray-800"
                      title="Eliminar"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr>
                <td colSpan={3} className="text-center px-4 py-10 text-slate-500 dark:text-gray-400">
                  No hay tareas registradas
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
