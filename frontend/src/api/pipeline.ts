import client from './client'

export interface PipelineRequest {
    video_url: string
    api_key: string
    voice_id?: number
    model_name?: string
    speed?: number
    skip_bgm?: boolean
    create_cover?: boolean
    publish_platforms?: string[]
    description?: string
    avatar_engine?: string
    subtitle_style?: Record<string, unknown>
    bgm_volume?: number
}

export const pipelineApi = {
    run: (data: PipelineRequest) =>
        client.post('/api/pipeline/run', data),
}
