import client from './client'

export const configApi = {
    getApiKeys: () =>
        client.get<{ keys: string[] }>('/api/config/apikeys'),

    addApiKey: (key: string) =>
        client.post('/api/config/apikeys', { key }),

    deleteApiKey: (key: string) =>
        client.request({ method: 'DELETE', url: '/api/config/apikeys', data: { key } }),

    checkServices: () =>
        client.get<{ cosyvoice: string; heygem: string; tuilionnx: string }>('/api/config/services'),
}
