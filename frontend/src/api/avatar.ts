import client from './client'

export interface AvatarModel {
    name: string
    path: string
}

export interface AvatarGenerateRequest {
    model_name: string
    audio_path: string
    engine: 'heygem' | 'tuilionnx'
    batch_size?: number
    sync_offset?: number
    scale_h?: number
    scale_w?: number
    compress_inference?: boolean
    beautify_teeth?: boolean
    add_watermark?: boolean
}

export const avatarApi = {
    listModels: () =>
        client.get<AvatarModel[]>('/api/avatar/models'),

    listFaces: () =>
        client.get('/api/avatar/faces'),

    generate: (data: AvatarGenerateRequest) =>
        client.post('/api/avatar/generate', data),

    checkHeygemStatus: () =>
        client.get<{ status: string }>('/api/avatar/service/heygem/status'),

    checkTuilionnxStatus: () =>
        client.get<{ status: string }>('/api/avatar/service/tuilionnx/status'),
}
