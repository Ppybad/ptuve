import { useState } from 'react'
import { createDownload } from '../api/downloads'
import { ArrowDownToLine, Loader2 } from 'lucide-react'
import { toast } from 'react-hot-toast'

interface Props {
  onCreated: () => void
}

export default function DownloadForm({ onCreated }: Props) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const disabled = loading || url.trim().length === 0

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (disabled) return
    setLoading(true)
    try {
      await createDownload(url.trim())
      toast.success('Descarga iniciada')
      setUrl('')
      onCreated()
    } catch (e) {
      toast.error('No se pudo iniciar la descarga')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-2xl mx-auto flex items-center gap-2 p-4">
      <input
        type="url"
        placeholder="Pega la URL del video..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={loading}
        className="flex-1 rounded-md bg-white border border-slate-300 text-slate-900 placeholder-slate-500 dark:bg-gray-900 dark:border-gray-700 dark:text-gray-100 dark:placeholder-gray-400 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled}
        className="inline-flex items-center gap-2 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-300 dark:disabled:bg-gray-600 px-4 py-3 font-medium text-white"
      >
        {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowDownToLine size={18} />}
        {loading ? 'Enviando…' : 'Descargar'}
      </button>
    </form>
  )
}
