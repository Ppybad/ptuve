import axios from 'axios'

const envBase = (import.meta as any)?.env?.VITE_API_BASE_URL as string | undefined
const hostBase = typeof window !== 'undefined'
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : 'http://localhost:8000'
const baseURL = (envBase && envBase.length > 0 ? envBase : hostBase) + '/api/v1'

export const apiClient = axios.create({
  baseURL,
  timeout: 30000,
})
