import axios from 'axios'

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
const backendHint =
    apiBaseUrl
    || (import.meta.env.DEV
        ? 'http://127.0.0.1:8000'
        : (typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000'))

const client = axios.create({
    baseURL: apiBaseUrl,
    timeout: 120000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor
client.interceptors.request.use(
    (config) => {
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor
client.interceptors.response.use(
    (response) => response,
    (error) => {
        let message = error.response?.data?.detail || error.message || '请求失败'

        if (!error.response) {
            if (error.code === 'ECONNABORTED' || /timeout/i.test(String(error.message || ''))) {
                message = '请求超时，请稍后重试'
            } else {
                message = `无法连接后端服务，请确认 API 服务已启动: ${backendHint}`
            }
        }

        error.message = message
        console.error('[API Error]', message)
        return Promise.reject(error)
    }
)

export default client
