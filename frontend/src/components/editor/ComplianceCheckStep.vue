<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { useConfigStore } from '../../stores/config'
import { scriptApi, type ProhibitedWordItem, type AiSuggestionItem } from '../../api/script'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const config = useConfigStore()

const apiKey = computed(() => config.apiKeys[0] || '')
const sourceText = computed(() => pipeline.rewrittenText || pipeline.extractedText || '')

// 审查结果
const passed = ref<boolean | null>(null)
const prohibitedWords = ref<ProhibitedWordItem[]>([])
const aiSuggestions = ref<AiSuggestionItem[]>([])
const revisedText = ref('')

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

async function handleCheck() {
  if (!sourceText.value) {
    ElMessage.warning('请先完成文案仿写')
    return
  }
  if (!apiKey.value) {
    ElMessage.warning('请在设置中配置 API Key')
    return
  }
  logs.value = []
  pipeline.setStepLoading('compliance', true)
  appendLog('开始合规审查...')
  try {
    const res = await scriptApi.complianceCheck({
      text: sourceText.value,
      api_key: apiKey.value,
    })
    passed.value = res.data.passed
    prohibitedWords.value = res.data.prohibited_words
    aiSuggestions.value = res.data.ai_suggestions
    revisedText.value = res.data.revised_text

    if (res.data.passed) {
      appendLog('✓ 审查通过，未发现合规风险')
      pipeline.reviewedText = sourceText.value
      pipeline.completeStep('compliance', { passed: true })
      pipeline.setActiveStep('synthesize')
      ElMessage.success('文案审查通过，无合规风险')
    } else {
      const total = prohibitedWords.value.length + aiSuggestions.value.length
      appendLog(`⚠ 发现 ${total} 处合规风险`)
      if (prohibitedWords.value.length > 0) {
        appendLog(`  违禁词：${prohibitedWords.value.map(w => w.word).join('、')}`)
      }
      if (aiSuggestions.value.length > 0) {
        appendLog(`  不合规表达：${aiSuggestions.value.length} 处，请查看详情`)
      }
      ElMessage.warning(`发现 ${total} 处合规风险，请查看`)
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || '合规审查失败'
    appendLog(`✗ 错误：${msg}`)
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('compliance', false)
  }
}

function handleAcceptRevised() {
  pipeline.reviewedText = revisedText.value
  pipeline.completeStep('compliance', { passed: false, accepted_revision: true })
  pipeline.setActiveStep('synthesize')
  ElMessage.success('已采用修正文案')
}

function handleSkip() {
  pipeline.reviewedText = sourceText.value
  pipeline.completeStep('compliance', { passed: false, skipped: true })
  pipeline.setActiveStep('synthesize')
  ElMessage.info('已跳过合规修正')
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">AI 检测违禁词和不合规表达，确保文案符合平台发布规范</p>

    <div class="source-text" v-if="sourceText">
      <p class="field-label">待审查文案</p>
      <div class="text-box">{{ sourceText }}</div>
    </div>
    <el-alert v-else type="info" :closable="false" title="请先完成文案仿写步骤" />

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.compliance.loading"
      :disabled="!sourceText"
      class="action-btn"
      @click="handleCheck"
    >
      {{ pipeline.steps.compliance.loading ? '审查中...' : '开始审查' }}
    </el-button>

    <div v-if="logs.length > 0" class="step-log">
      <p class="result-label">执行日志</p>
      <div ref="logBoxRef" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
    </div>

    <!-- 审查结果 -->
    <div v-if="passed !== null" class="review-result">
      <!-- 通过状态 -->
      <div v-if="passed" class="status-banner status-pass">
        <span class="status-icon">&#10003;</span>
        <span>文案审查通过，未发现合规风险</span>
      </div>

      <!-- 未通过状态 -->
      <template v-else>
        <div class="status-banner status-fail">
          <span class="status-icon">!</span>
          <span>发现 {{ prohibitedWords.length + aiSuggestions.length }} 处合规风险</span>
        </div>

        <!-- 违禁词列表 -->
        <div v-if="prohibitedWords.length > 0" class="issue-section">
          <p class="issue-title">违禁词命中</p>
          <div class="issue-list">
            <div v-for="(item, idx) in prohibitedWords" :key="'pw-' + idx" class="issue-item">
              <span class="issue-word">{{ item.word }}</span>
              <span class="issue-category">{{ item.category }}</span>
            </div>
          </div>
        </div>

        <!-- AI 建议列表 -->
        <div v-if="aiSuggestions.length > 0" class="issue-section">
          <p class="issue-title">不合规表达</p>
          <div class="issue-list">
            <div v-for="(item, idx) in aiSuggestions" :key="'ai-' + idx" class="suggestion-item">
              <div class="suggestion-row">
                <span class="suggestion-original">{{ item.original }}</span>
                <span class="suggestion-arrow">&rarr;</span>
                <span class="suggestion-fix">{{ item.suggestion }}</span>
              </div>
              <p class="suggestion-reason">{{ item.reason }}</p>
            </div>
          </div>
        </div>

        <!-- 修正后文案 -->
        <div class="revised-section">
          <p class="field-label">修正后文案</p>
          <el-input
            v-model="revisedText"
            type="textarea"
            :rows="6"
            placeholder="修正后的文案..."
          />
        </div>

        <!-- 操作按钮 -->
        <div class="action-group">
          <el-button type="primary" size="large" class="action-btn" @click="handleAcceptRevised">
            采用修正文案
          </el-button>
          <el-button size="large" class="action-btn" @click="handleSkip">
            忽略并继续
          </el-button>
        </div>
      </template>
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

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
}

.review-result {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.status-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.status-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.status-pass {
  background: rgba(76, 175, 80, 0.08);
  color: var(--color-success);
}

.status-pass .status-icon {
  background: var(--color-success);
  color: #fff;
}

.status-fail {
  background: rgba(229, 57, 53, 0.08);
  color: var(--color-error);
}

.status-fail .status-icon {
  background: var(--color-error);
  color: #fff;
}

.issue-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.issue-title {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.issue-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
}

.issue-word {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-error);
}

.issue-category {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-page);
  padding: 2px var(--space-2);
  border-radius: var(--radius-full);
}

.suggestion-item {
  padding: var(--space-3);
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
}

.suggestion-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  margin-bottom: var(--space-1);
}

.suggestion-original {
  font-size: var(--text-sm);
  color: var(--color-error);
  text-decoration: line-through;
}

.suggestion-arrow {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.suggestion-fix {
  font-size: var(--text-sm);
  color: var(--color-success);
  font-weight: var(--font-medium);
}

.suggestion-reason {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

.revised-section {
  display: flex;
  flex-direction: column;
}

.action-group {
  display: flex;
  gap: var(--space-3);
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
