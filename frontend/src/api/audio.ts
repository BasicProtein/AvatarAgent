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

export interface SynthesizeResponse {
    audio_path: string   // 服务端绝对路径，供数字人步骤使用
    audio_url: string    // HTTP 访问路径，供浏览器播放
    duration: number
}

export interface VoiceTrainRequest {
    name: string
    audio_path: string
}

export const audioApi = {
    /** 获取已注册音色列表 */
    listVoices: () =>
        client.get<VoiceItem[]>('/api/audio/voices'),

    /**
     * 语音合成 — 返回 JSON（含服务端绝对路径）
     * 用于：合成完成后将 audio_path 传给数字人生成步骤
     */
    synthesizePath: (data: SynthesizeRequest) =>
        client.post<SynthesizeResponse>('/api/audio/synthesize/path', data),

    /**
     * 语音合成 — 直接返回 WAV 二进制流
     * 用于：直接下载/预听，不需要路径的场景
     */
    synthesize: (data: SynthesizeRequest) =>
        client.post('/api/audio/synthesize', data, { responseType: 'blob' }),

    /** 上传参考音频文件 */
    uploadSample: (file: File) => {
        const form = new FormData()
        form.append('file', file)
        return client.post<{ path: string; filename: string }>('/api/audio/upload', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
        })
    },

    /** 训练（注册）新音色 */
    trainVoice: (data: VoiceTrainRequest) =>
        client.post('/api/audio/train', data),

    /** 删除音色 */
    deleteVoice: (name: string) =>
        client.delete(`/api/audio/voices/${encodeURIComponent(name)}`),

    /** 预览音色参考音频（返回音频 blob） */
    previewVoice: (name: string) =>
        client.get(`/api/audio/voices/${encodeURIComponent(name)}/preview`, { responseType: 'blob' }),

    /** 重命名音色 */
    renameVoice: (name: string, newName: string) =>
        client.put(`/api/audio/voices/${encodeURIComponent(name)}`, null, {
            params: { new_name: newName },
        }),

    /** CosyVoice 服务状态 */
    checkStatus: () =>
        client.get<{ status: string }>('/api/audio/service/status'),
}
