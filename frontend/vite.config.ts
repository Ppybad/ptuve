import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: ['all', 'd2ba-189-240-208-186.ngrok-free.app'],
  },
  preview: {
    host: true,
    allowedHosts: ['all', 'd2ba-189-240-208-186.ngrok-free.app'],
  },
})
