import client from './client'

export interface AvatarModel {
    name: string
    path: string
}

export interface SavedAvatar {
    name: string
    description: string
    video_path: string
    model_dir: string
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

export interface AvatarSaveRequest {
    name: string
    video_path: string
    description?: string
}

export const avatarApi = {
    /** HeyGem 模型目录列表 */
    listModels: () =>
        client.get<AvatarModel[]>('/api/avatar/models'),

    /** TuiliONNX 人物列表 */
    listFaces: () =>
        client.get('/api/avatar/faces'),

    /** 已保存的自定义形象列表 */
    listSaved: () =>
        client.get<SavedAvatar[]>('/api/avatar/saved'),

    /**
     * 上传人脸视频文件
     * 返回服务端路径，供后续 saveAvatar 使用
     */
    uploadVideo: (file: File) => {
        const form = new FormData()
        form.append('file', file)
        return client.post<{ path: string; filename: string }>(
            '/api/avatar/upload',
            form,
            { headers: { 'Content-Type': 'multipart/form-data' } },
        )
    },

    /** 保存形象（注册为数字人模型） */
    saveAvatar: (data: AvatarSaveRequest) =>
        client.post('/api/avatar/save', data),

    /** 删除已保存的自定义形象 */
    deleteAvatar: (name: string) =>
        client.delete(`/api/avatar/saved/${encodeURIComponent(name)}`),

    /** 生成数字人视频 */
    generate: (data: AvatarGenerateRequest) =>
        client.post('/api/avatar/generate', data),

    checkHeygemStatus: () =>
        client.get<{ status: string }>('/api/avatar/service/heygem/status'),

    checkTuilionnxStatus: () =>
        client.get<{ status: string }>('/api/avatar/service/tuilionnx/status'),
}
