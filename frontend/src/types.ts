export type DownloadStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface DownloadTask {
  id: string
  url: string
  title: string | null
  status: DownloadStatus
  file_path: string | null
  created_at: string
}

export interface PaginatedTasks {
  items: DownloadTask[]
  total: number
  skip: number
  limit: number
  has_more: boolean
}
