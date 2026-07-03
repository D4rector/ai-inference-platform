import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref(localStorage.getItem('access_token') || '')

  async function login(username: string, password: string) {
    const { data } = await api.post('/token/', { username, password })
    token.value = data.access
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    user.value = { username }
    return data
  }

  async function register(username: string, password: string, email: string) {
    await api.post('/register/', { username, password, email })
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  return { user, token, login, register, logout }
})
