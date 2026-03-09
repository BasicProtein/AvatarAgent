import axios from 'axios'

const client = axios.create({
    baseURL: 'http://localhost:8000',
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
        const message = error.response?.data?.detail || error.message || '请求失败'
        error.message = message
        console.error('[API Error]', message)
        return Promise.reject(error)
    }
)

export default client
