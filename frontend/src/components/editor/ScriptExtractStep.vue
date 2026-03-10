<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { usePipelineStore } from '../../stores/pipeline'
import { scriptApi } from '../../api/script'
import { ElMessage } from 'element-plus'
import type { AxiosError } from 'axios'

const pipeline = usePipelineStore()
const router = useRouter()
const videoUrl = ref('')
const extractError = ref('')

const logs = ref<string[]>([])
const logBoxRef = ref<HTMLElement | null>(null)

function appendLog(msg: string) {
  const now = new Date()
  const ts = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  logs.value.push(`[${ts}] ${msg}`)
  nextTick(() => {
    if (logBoxRef.value) logBoxRef.value.scrollTop = logBoxRef.value.scrollHeight
  })
}

function goToSettings() {
  router.push('/settings')
}

async function handleExtract() {
  if (!videoUrl.value.trim()) {
    ElMessage.warning('请输入视频链接')
    return
  }
  extractError.value = ''
  logs.value = []
  pipeline.setStepLoading('extract', true)
  appendLog('开始提取视频文案...')
  try {
    appendLog(`视频链接：${videoUrl.value.trim()}`)
    const res = await scriptApi.extract({ video_url: videoUrl.value.trim() })
    pipeline.extractedText = res.data.text
    pipeline.completeStep('extract', { text: res.data.text })
    pipeline.setActiveStep('rewrite')
    appendLog(`✓ 提取成功，共 ${res.data.text.length} 字`)
    ElMessage.success('文案提取成功')
  } catch (e: unknown) {
    const axiosErr = e as AxiosError<{ detail?: string }>
    const detail = axiosErr?.response?.data?.detail || ''
    const msg = detail || (e instanceof Error ? e.message : '文案提取失败')

    if (msg.includes('显存不足') || msg.toLowerCase().includes('out of memory')) {
      extractError.value = 'gpu_oom'
      appendLog('✗ 错误：GPU 显存不足，请切换为 CPU 推理')
    } else {
      extractError.value = msg
      appendLog(`✗ 错误：${msg}`)
    }
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('extract', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">粘贴对标视频链接，自动提取口播文案</p>
    <el-input
      v-model="videoUrl"
      placeholder="请粘贴抖音/快手等平台视频链接..."
      size="large"
      clearable
    >
      <template #prefix>
        <el-icon><Link /></el-icon>
      </template>
    </el-input>
    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.extract.loading"
      :disabled="!videoUrl.trim()"
      class="action-btn"
      @click="handleExtract"
    >
      {{ pipeline.steps.extract.loading ? '提取中...' : '开始提取' }}
    </el-button>
    <!-- GPU 显存不足提示 -->
    <div v-if="extractError === 'gpu_oom'" class="error-banner oom">
      <div class="error-icon">&#x26A0;&#xFE0F;</div>
      <div class="error-body">
        <p class="error-title">GPU 显存不足</p>
        <p class="error-desc">
          Whisper 语音识别模型无法加载到 GPU，可能是其他服务（如 CosyVoice）占用了显存。
        </p>
        <p class="error-action">
          前往 <a href="#" @click.prevent="goToSettings">设置 → 本地 ASR</a> 将推理设备切换为 <strong>CPU</strong>，或关闭其他占用显存的程序后重试。
        </p>
      </div>
    </div>
    <!-- 其他错误提示 -->
    <div v-else-if="extractError" class="error-banner">
      <p class="error-desc">{{ extractError }}</p>
    </div>

    <div v-if="logs.length > 0" class="step-log">
      <p class="result-label">执行日志</p>
      <div ref="logBoxRef" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
    </div>

    <div v-if="pipeline.extractedText" class="result-preview">
      <p class="result-label">提取结果</p>
      <div class="result-text">{{ pipeline.extractedText }}</div>
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
  line-height: var(--leading-relaxed);
}

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
}

.result-preview {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}

.result-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
}

.result-text {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.error-banner {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  background: rgba(192, 57, 43, 0.06);
  border: 1px solid rgba(192, 57, 43, 0.2);
  color: var(--color-text-primary);
}

.error-banner.oom {
  background: rgba(243, 156, 18, 0.06);
  border-color: rgba(243, 156, 18, 0.3);
}

.error-icon { font-size: var(--text-xl); line-height: 1; }
.error-body { flex: 1; }
.error-title { font-size: var(--text-sm); font-weight: var(--font-semibold); margin-bottom: var(--space-1); }
.error-desc { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.5; }
.error-action { font-size: var(--text-sm); color: var(--color-text-secondary); margin-top: var(--space-2); }
.error-action a { color: var(--color-primary); text-decoration: underline; cursor: pointer; }

.step-log {
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
</style>
