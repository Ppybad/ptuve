import { apiClient } from './apiClient'
import type { PaginatedTasks, DownloadTask } from '../types'

export async function fetchDownloads(
  skip = 0,
  limit = 10,
  search?: string,
  status?: string,
): Promise<PaginatedTasks> {
  const params: Record<string, string | number> = { skip, limit }
  if (search && search.trim()) params.search = search.trim()
  if (status && status !== 'ALL') params.status = status
  const { data } = await apiClient.get<PaginatedTasks>('/downloads', { params })
  return data
}

export async function createDownload(url: string): Promise<DownloadTask> {
  const { data } = await apiClient.post<DownloadTask>('/downloads', { url })
  return data
}

export async function retryDownload(id: string): Promise<DownloadTask> {
  const { data } = await apiClient.post<DownloadTask>(`/downloads/${id}/retry`)
  return data
}

export async function deleteDownload(id: string): Promise<{ id: string; deleted: boolean }> {
  const { data } = await apiClient.delete<{ id: string; deleted: boolean }>(`/downloads/${id}`)
  return data
}

export function getDownloadFileUrl(id: string): string {
  return `${apiClient.defaults.baseURL}/downloads/${id}/file`
}
