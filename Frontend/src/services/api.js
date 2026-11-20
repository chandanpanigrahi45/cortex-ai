import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cortex_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const registerUser = async (username, email, password) => {
  const res = await api.post('/users/', { username, email, password })
  return res.data
}

export const loginUser = async (email, password) => {
  const res = await api.post('/users/login', { email, password })
  return res.data
}

export const getUser = async () => {
  const res = await api.get('/users/me')
  return res.data
}

export const getUserCredits = async () => {
  const res = await api.get('/credits/me')
  return res.data
}

export const createPaymentOrder = async (packageId) => {
  const res = await api.post('/payments/orders', { package_id: packageId })
  return res.data
}

export const verifyPayment = async (payment) => {
  const res = await api.post('/payments/verify', payment)
  return res.data
}

export const routeRequest = async (request, destination) => {
  const res = await api.post('/route/', {
    request,
    ...(destination && destination !== 'auto' ? { destination } : {}),
  })
  return res.data
}

export const checkHealth = async () => {
  const res = await api.get('/health')
  return res.data
}
