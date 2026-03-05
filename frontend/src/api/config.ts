import client from './client'

export interface CloudGpuConfig {
    enabled: boolean
    api_url: string
    api_key: string
}

export interface LocalAsrStatus {
    whisper_installed: boolean
    torch_installed: boolean
    device: 'cuda' | 'mps' | 'cpu'
    gpu_name: string | null
    cuda_available: boolean
    model_size: string
}

export const configApi = {
    getApiKeys: () =>
        client.get<{ keys: string[] }>('/api/config/apikeys'),

    addApiKey: (key: string) =>
        client.post('/api/config/apikeys', { key }),

    deleteApiKey: (key: string) =>
        client.request({ method: 'DELETE', url: '/api/config/apikeys', data: { key } }),

    checkServices: () =>
        client.get<{ cosyvoice: string; heygem: string; tuilionnx: string }>('/api/config/services'),

    // ── 云端 GPU ──────────────────────────────────────────────────────────────

    getCloudGpu: () =>
        client.get<CloudGpuConfig>('/api/config/cloud-gpu'),

    setCloudGpu: (data: CloudGpuConfig) =>
        client.post('/api/config/cloud-gpu', data),

    testCloudGpu: () =>
        client.post<{ status: string; model?: string; message?: string }>('/api/config/cloud-gpu/test', {}),

    // ── 本地 ASR（Whisper）────────────────────────────────────────────────────

    getLocalAsr: () =>
        client.get<LocalAsrStatus>('/api/config/local-asr'),

    setWhisperModel: (model_size: string) =>
        client.post<{ status: string; model_size: string }>('/api/config/local-asr', { model_size }),
}
