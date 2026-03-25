import axios from 'axios'

export const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
})
