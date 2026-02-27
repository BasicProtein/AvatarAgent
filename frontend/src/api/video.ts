import client from './client'

export interface SubtitleStyle {
    font_family: string
    font_size: number
    font_color: string
    outline_color: string
    bottom_margin: number
}

export interface SubtitleRequest {
    video_path: string
    text?: string
    api_key?: string
    style?: SubtitleStyle
}

export interface BGMRequest {
    video_path: string
    bgm_name?: string
    volume: number
}

export interface CoverRequest {
    video_path: string
    text?: string
    highlight_words?: string
    use_ai: boolean
    api_key?: string
    font_family?: string
    font_size?: number
    font_color?: string
    highlight_color?: string
    position?: string
    frame_time?: number
}

export const videoApi = {
    listFonts: () =>
        client.get<{ fonts: string[] }>('/api/video/fonts'),

    addSubtitle: (data: SubtitleRequest) =>
        client.post('/api/video/subtitle', data),

    listBgm: () =>
        client.get<{ bgm_list: Array<{ name: string; path: string }> }>('/api/video/bgm'),

    addBgm: (data: BGMRequest) =>
        client.post('/api/video/bgm/add', data),

    generateCover: (data: CoverRequest) =>
        client.post('/api/video/cover', data),
}
