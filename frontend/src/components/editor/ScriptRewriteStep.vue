<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { useConfigStore } from '../../stores/config'
import { scriptApi } from '../../api/script'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const config = useConfigStore()
const mode = ref<'auto' | 'custom'>('auto')
const customPrompt = ref('')

const apiKey = computed(() => config.apiKeys[0] || '')
const sourceText = computed(() => pipeline.extractedText || '')

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

async function handleRewrite() {
  if (!sourceText.value) {
    ElMessage.warning('请先提取文案')
    return
  }
  if (!apiKey.value) {
    ElMessage.warning('请在设置中配置 API Key')
    return
  }
  logs.value = []
  pipeline.setStepLoading('rewrite', true)
  appendLog('开始文案仿写...')
  try {
    appendLog(`模式：${mode.value === 'auto' ? 'AI 自动仿写' : '自定义指令'}`)
    const res = await scriptApi.rewrite({
      text: sourceText.value,
      api_key: apiKey.value,
      mode: mode.value,
      prompt: mode.value === 'custom' ? customPrompt.value : undefined,
    })
    pipeline.rewrittenText = res.data.text
    appendLog(`✓ 仿写完成，共 ${res.data.text.length} 字`)
    // Also generate description
    appendLog('生成视频描述...')
    const descRes = await scriptApi.generateDescription({
      text: res.data.text,
      api_key: apiKey.value,
    })
    pipeline.description = descRes.data.text
    appendLog('✓ 描述生成完成')
    pipeline.completeStep('rewrite', { text: res.data.text })
    pipeline.setActiveStep('compliance')
    ElMessage.success('文案仿写成功')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '文案仿写失败'
    appendLog(`✗ 错误：${msg}`)
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('rewrite', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">基于提取的文案进行 AI 仿写改写</p>

    <div class="source-text" v-if="sourceText">
      <p class="field-label">原始文案</p>
      <div class="text-box">{{ sourceText }}</div>
    </div>
    <el-alert v-else type="info" :closable="false" title="请先完成文案提取步骤" />

    <div class="mode-select">
      <p class="field-label">仿写模式</p>
      <el-radio-group v-model="mode">
        <el-radio-button value="auto">AI 自动仿写</el-radio-button>
        <el-radio-button value="custom">自定义指令</el-radio-button>
      </el-radio-group>
    </div>

    <el-input
      v-if="mode === 'custom'"
      v-model="customPrompt"
      type="textarea"
      :rows="3"
      placeholder="输入自定义仿写指令，例如：改为更正式的语气..."
    />

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.rewrite.loading"
      :disabled="!sourceText"
      class="action-btn"
      @click="handleRewrite"
    >
      {{ pipeline.steps.rewrite.loading ? '仿写中...' : '开始仿写' }}
    </el-button>

    <div v-if="logs.length > 0" class="step-log">
      <p class="result-label">执行日志</p>
      <div ref="logBoxRef" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
    </div>

    <div v-if="pipeline.rewrittenText" class="result-preview">
      <p class="result-label">仿写结果</p>
      <el-input
        v-model="pipeline.rewrittenText"
        type="textarea"
        :rows="6"
        placeholder="仿写后的文案..."
      />
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

.field-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.source-text .text-box {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

.mode-select {
  display: flex;
  flex-direction: column;
}

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
}

.result-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.result-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
}

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
