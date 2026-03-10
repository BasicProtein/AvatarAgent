import client from './client'

export type SynthesizeStreamEvent =
    | { type: 'log'; message: string }
    | { type: 'result'; audio_path: string; audio_url: string; duration: number }
    | { type: 'error'; message: string }

/**
 * 语音合成 SSE 流式接口，通过 fetch POST 消费 text/event-stream。
 * 调用方传入 onEvent 回调接收每一条事件，传入 signal 可取消。
 */
export async function synthesizeStream(
    data: { text: string; voice_id: number; speed: number },
    onEvent: (event: SynthesizeStreamEvent) => void,
    signal?: AbortSignal,
): Promise<void> {
    const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')
    const url = `${apiBaseUrl}/api/audio/synthesize/stream`

    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
        signal,
    })

    if (!response.ok) {
        // 如果流式端点不存在（后端未重启），降级到普通 JSON 接口
        if (response.status === 404) {
            onEvent({ type: 'log', message: '流式接口不可用，使用普通模式合成...' })
            const fallback = await client.post<{ audio_path: string; audio_url: string; duration: number }>(
                '/api/audio/synthesize/path',
                data,
                { timeout: 600000 },
            )
            onEvent({ type: 'result', ...fallback.data })
            return
        }
        let detail = response.statusText
        try {
            const json = await response.json()
            detail = json?.detail || detail
        } catch { /* ignore */ }
        throw new Error(detail)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data:')) continue
            const payload = trimmed.slice(5).trim()
            if (!payload) continue
            try {
                onEvent(JSON.parse(payload) as SynthesizeStreamEvent)
            } catch { /* ignore malformed */ }
        }
    }
}

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
        client.post<SynthesizeResponse>('/api/audio/synthesize/path', data, {
            timeout: 600000,
        }),

    /**
     * 语音合成 — 直接返回 WAV 二进制流
     * 用于：直接下载/预听，不需要路径的场景
     */
    synthesize: (data: SynthesizeRequest) =>
        client.post('/api/audio/synthesize', data, {
            responseType: 'blob',
            timeout: 600000,
        }),

    /** 根据已生成的音频路径拉取 blob，供浏览器本地预听 */
    fetchAudioBlob: (audioPath: string) =>
        client.post('/api/audio/generated', {
            audio_path: audioPath,
        }, {
            responseType: 'blob',
            timeout: 600000,
        }),

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
