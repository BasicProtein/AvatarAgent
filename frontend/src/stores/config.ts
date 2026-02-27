import { defineStore } from 'pinia'
import { ref } from 'vue'
import { configApi } from '../api/config'

export const useConfigStore = defineStore('config', () => {
    const theme = ref<'light' | 'dark'>('light')
    const apiKeys = ref<string[]>([])
    const services = ref<{ cosyvoice: string; heygem: string; tuilionnx: string }>({
        cosyvoice: 'offline',
        heygem: 'offline',
        tuilionnx: 'offline',
    })

    function toggleTheme() {
        theme.value = theme.value === 'light' ? 'dark' : 'light'
        document.documentElement.setAttribute('data-theme', theme.value)
        localStorage.setItem('avatar-agent-theme', theme.value)
    }

    function initTheme() {
        const saved = localStorage.getItem('avatar-agent-theme') as 'light' | 'dark' | null
        if (saved) {
            theme.value = saved
            document.documentElement.setAttribute('data-theme', saved)
        }
    }

    async function fetchApiKeys() {
        try {
            const res = await configApi.getApiKeys()
            apiKeys.value = res.data.keys
        } catch {
            console.error('获取 API Key 失败')
        }
    }

    async function fetchServices() {
        try {
            const res = await configApi.checkServices()
            services.value = res.data
        } catch {
            console.error('获取服务状态失败')
        }
    }

    return {
        theme,
        apiKeys,
        services,
        toggleTheme,
        initTheme,
        fetchApiKeys,
        fetchServices,
    }
})
