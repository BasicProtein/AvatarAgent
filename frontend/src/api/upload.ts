import client from './client'

export interface PublishRequest {
    video_path: string
    description: string
    cover_path?: string
    tags?: string[]
}

export const uploadApi = {
    publishDouyin: (data: PublishRequest) =>
        client.post('/api/upload/douyin', data),

    publishXiaohongshu: (data: PublishRequest) =>
        client.post('/api/upload/xiaohongshu', data),

    publishShipinhao: (data: PublishRequest) =>
        client.post('/api/upload/shipinhao', data),

    publishAll: (data: PublishRequest) =>
        client.post('/api/upload/all', data),
}
