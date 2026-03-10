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

/**
 * SSE 流式生成数字人视频
 * 回调 onLog 接收进度日志，onResult 接收最终视频路径，onError 接收错误信息
 */
export function generateAvatarStream(
    data: AvatarGenerateRequest,
    onLog: (msg: string) => void,
    onResult: (videoPath: string) => void,
    onError: (msg: string) => void,
): () => void {
    const ctrl = new AbortController()

    ;(async () => {
        try {
            const resp = await fetch('/api/avatar/generate/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
                signal: ctrl.signal,
            })
            if (!resp.ok || !resp.body) {
                onError(`请求失败: ${resp.status}`)
                return
            }
            const reader = resp.body.getReader()
            const decoder = new TextDecoder()
            let buf = ''
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                buf += decoder.decode(value, { stream: true })
                const lines = buf.split('\n')
                buf = lines.pop() ?? ''
                for (const line of lines) {
                    if (!line.startsWith('data:')) continue
                    try {
                        const ev = JSON.parse(line.slice(5).trim())
                        if (ev.type === 'log') onLog(ev.message)
                        else if (ev.type === 'result') onResult(ev.video_path ?? '')
                        else if (ev.type === 'error') onError(ev.message)
                    } catch { /* skip malformed */ }
                }
            }
        } catch (e: unknown) {
            if ((e as { name?: string })?.name !== 'AbortError') {
                onError(e instanceof Error ? e.message : '生成失败')
            }
        }
    })()

    return () => ctrl.abort()
}
