import client from './client'

export interface VoiceItem {
    name: string
    path: string
}

export interface SynthesizeRequest {
    text: string
    voice_id: number
    speed: number
}

export const audioApi = {
    listVoices: () =>
        client.get<VoiceItem[]>('/api/audio/voices'),

    synthesize: (data: SynthesizeRequest) =>
        client.post('/api/audio/synthesize', data, { responseType: 'blob' }),

    checkStatus: () =>
        client.get<{ status: string }>('/api/audio/service/status'),
}
