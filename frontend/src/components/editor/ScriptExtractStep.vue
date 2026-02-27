<script setup lang="ts">
import { ref } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { scriptApi } from '../../api/script'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const videoUrl = ref('')

async function handleExtract() {
  if (!videoUrl.value.trim()) {
    ElMessage.warning('请输入视频链接')
    return
  }
  pipeline.setStepLoading('extract', true)
  try {
    const res = await scriptApi.extract({ video_url: videoUrl.value.trim() })
    pipeline.extractedText = res.data.text
    pipeline.completeStep('extract', { text: res.data.text })
    pipeline.setActiveStep('rewrite')
    ElMessage.success('文案提取成功')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '文案提取失败'
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
</style>
