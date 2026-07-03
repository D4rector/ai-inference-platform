import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// 请求拦截：自动带 token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：401 自动踢到登录页
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      router.push('/login')
    }
    return Promise.reject(error)
  },
)

export default api
