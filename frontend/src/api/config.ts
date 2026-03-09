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
    whisper_device: 'auto' | 'cuda' | 'cpu'
}

export interface CosyVoiceRuntimeStatus {
    device: 'gpu' | 'cpu'
    model_dir: string
    torch_cuda_available: boolean
    gpu_name: string | null
    onnxruntime_gpu_installed: boolean
    onnxruntime_providers: string[]
    onnxruntime_cuda_session_ready?: boolean
    onnxruntime_cuda_session_providers?: string[]
    onnxruntime_cuda_error?: string
    main_model_gpu_ready?: boolean
    full_gpu_ready?: boolean
    can_use_gpu: boolean
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
        client.post<{ status: string; model_size: string; device: string }>('/api/config/local-asr', { model_size }),

    setWhisperDevice: (device: 'auto' | 'cuda' | 'cpu') =>
        client.post<{ status: string; model_size: string; device: string }>('/api/config/local-asr', { device }),

    getCosyVoiceRuntime: () =>
        client.get<CosyVoiceRuntimeStatus>('/api/config/cosyvoice-runtime'),

    setCosyVoiceRuntime: (device: 'gpu' | 'cpu') =>
        client.post<{ status: string; device: 'gpu' | 'cpu'; message: string }>(
            '/api/config/cosyvoice-runtime',
            { device },
        ),
}
