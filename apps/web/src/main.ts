import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { configureClient } from '@gozero-monorepo/api-client'

configureClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL,
  getToken: () => localStorage.getItem('token'),
})

createApp(App).use(router).mount('#app')
