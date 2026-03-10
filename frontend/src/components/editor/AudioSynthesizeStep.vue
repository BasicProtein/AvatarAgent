<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { audioApi, synthesizeStream, type VoiceItem } from '../../api/audio'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const voices = ref<VoiceItem[]>([])
const selectedVoice = ref(0)
const speed = ref(1.0)
const audioUrl = ref('')   // 浏览器本地播放 URL（Blob 或 /output/ 路径）

const logs = ref<string[]>([])
const logBoxRef = ref<HTMLElement | null>(null)

function revokeAudioUrl(url: string) {
  if (url.startsWith('blob:')) {
    URL.revokeObjectURL(url)
  }
}

function appendLog(msg: string) {
  const now = new Date()
  const ts = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  logs.value.push(`[${ts}] ${msg}`)
  nextTick(() => {
    if (logBoxRef.value) {
      logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
    }
  })
}

let abortController: AbortController | null = null

onMounted(async () => {
  try {
    const res = await audioApi.listVoices()
    voices.value = res.data
  } catch { /* ignore */ }
})

onBeforeUnmount(() => {
  revokeAudioUrl(audioUrl.value)
  abortController?.abort()
})

async function handleSynthesize() {
  const text = pipeline.reviewedText || pipeline.rewrittenText || pipeline.extractedText
  if (!text) {
    ElMessage.warning('请先完成文案步骤')
    return
  }

  logs.value = []
  abortController?.abort()
  abortController = new AbortController()

  pipeline.setStepLoading('synthesize', true)
  appendLog('开始语音合成...')

  try {
    let resultAudioPath = ''
    let resultAudioUrl = ''
    let hasError = false

    await synthesizeStream(
      { text, voice_id: selectedVoice.value, speed: speed.value },
      (event) => {
        if (event.type === 'log') {
          appendLog(event.message)
        } else if (event.type === 'result') {
          resultAudioPath = event.audio_path
          resultAudioUrl = event.audio_url
          appendLog('✓ 合成成功！')
        } else if (event.type === 'error') {
          hasError = true
          appendLog(`✗ 错误：${event.message}`)
        }
      },
      abortController.signal,
    )

    if (hasError || !resultAudioPath) {
      throw new Error('语音合成失败，请查看日志')
    }

    // 存入 pipeline：供数字人步骤使用的服务端绝对路径
    pipeline.audioPath = resultAudioPath

    // 构造浏览器可播放的 URL
    revokeAudioUrl(audioUrl.value)
    if (resultAudioUrl) {
      try {
        const previewRes = await audioApi.fetchAudioBlob(resultAudioPath)
        audioUrl.value = URL.createObjectURL(new Blob([previewRes.data], { type: 'audio/wav' }))
      } catch {
        audioUrl.value = resultAudioUrl
      }
    } else {
      audioUrl.value = ''
    }

    pipeline.completeStep('synthesize', { audio_path: resultAudioPath })
    pipeline.setActiveStep('avatar')
    ElMessage.success('语音合成成功')
  } catch (e: unknown) {
    if ((e as { name?: string })?.name === 'AbortError') return
    const msg = e instanceof Error ? e.message : '语音合成失败'
    appendLog(`✗ ${msg}`)
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('synthesize', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">选择音色和语速，将文案合成为语音</p>

    <div class="field">
      <p class="field-label">选择音色</p>
      <el-select v-model="selectedVoice" placeholder="选择音色" style="width: 100%;" size="large">
        <el-option
          v-for="(voice, idx) in voices"
          :key="idx"
          :label="voice.name"
          :value="idx"
        />
        <el-option v-if="voices.length === 0" label="暂无音色（请先在声音管理中添加）" :value="0" disabled />
      </el-select>
    </div>

    <div class="field">
      <p class="field-label">语速调节 ({{ speed.toFixed(1) }}x)</p>
      <el-slider v-model="speed" :min="0.5" :max="2.0" :step="0.1" :show-tooltip="false" />
    </div>

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.synthesize.loading"
      class="action-btn"
      @click="handleSynthesize"
    >
      {{ pipeline.steps.synthesize.loading ? '合成中...' : '开始合成' }}
    </el-button>

    <div v-if="logs.length > 0" class="synth-log">
      <p class="result-label">合成日志</p>
      <div ref="logBoxRef" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
    </div>

    <div v-if="audioUrl" class="audio-preview">
      <p class="result-label">合成结果</p>
      <audio :src="audioUrl" controls style="width: 100%;" />
    </div>

    <div v-if="pipeline.audioPath && !audioUrl" class="audio-preview">
      <p class="result-label">合成完成</p>
      <p class="result-path">{{ pipeline.audioPath }}</p>
    </div>
  </div>
</template>

<style scoped>
.step-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.step-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.field {
  display: flex;
  flex-direction: column;
}

.field-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
}

.synth-log {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  background: rgba(250, 249, 245, 0.6);
}

.log-box {
  max-height: 160px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-line {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  line-height: 1.6;
  word-break: break-all;
  margin: 0;
}

.audio-preview {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.result-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.result-path {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  word-break: break-all;
}
</style>
