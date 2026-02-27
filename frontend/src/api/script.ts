import client from './client'

export interface ExtractRequest {
    video_url: string
}

export interface RewriteRequest {
    text: string
    api_key: string
    mode: 'auto' | 'custom'
    prompt?: string
}

export interface DescriptionRequest {
    text: string
    api_key: string
}

export const scriptApi = {
    extract: (data: ExtractRequest) =>
        client.post<{ text: string }>('/api/script/extract', data),

    rewrite: (data: RewriteRequest) =>
        client.post<{ text: string }>('/api/script/rewrite', data),

    generateDescription: (data: DescriptionRequest) =>
        client.post<{ text: string }>('/api/script/description', data),
}
