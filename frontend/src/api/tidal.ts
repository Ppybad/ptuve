import { apiClient } from './apiClient'

export type TidalType = 'track' | 'album' | 'artist'

export interface TidalItem {
  id: number
  title: string
  artist?: string | null
  album_name?: string | null
  image?: string | null
}

export interface TidalSearchResponse {
  items: TidalItem[]
}

export async function searchTidal(query: string, type: TidalType = 'track'): Promise<TidalItem[]> {
  const { data } = await apiClient.get<TidalSearchResponse>('/tidal/search', { params: { query, type } })
  return data.items
}

export async function enqueueTidalDownload(id: number, type: 'track' | 'album'): Promise<{ enqueued: number }> {
  const { data } = await apiClient.post<{ enqueued: number; items: { id: string }[] }>('/tidal/download', { id, type })
  return { enqueued: data.enqueued }
}

export async function getTidalLogin(): Promise<{ status: string; link?: string; code?: string }> {
  const { data } = await apiClient.get('/tidal/login')
  return data
}

export async function getTidalStatus(): Promise<{ status: 'connected' | 'awaiting_authorization' }> {
  const { data } = await apiClient.get('/tidal/status')
  return data
}
