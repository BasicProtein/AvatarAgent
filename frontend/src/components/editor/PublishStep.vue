<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { uploadApi } from '../../api/upload'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()

const platforms = ref({
  douyin: true,
  xiaohongshu: true,
  shipinhao: true,
})

const description = ref('')
const tags = ref('')

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

async function handlePublish() {
  const videoPath = pipeline.finalVideoPath || pipeline.avatarVideoPath
  if (!videoPath) {
    ElMessage.warning('请先完成视频制作')
    return
  }

  const selectedPlatforms = Object.entries(platforms.value)
    .filter(([, v]) => v)
    .map(([k]) => k)

  if (selectedPlatforms.length === 0) {
    ElMessage.warning('请至少选择一个发布平台')
    return
  }

  logs.value = []
  pipeline.setStepLoading('publish', true)
  appendLog('开始发布视频...')
  appendLog(`目标平台：${selectedPlatforms.join('、')}`)
  try {
    const data = {
      video_path: videoPath,
      description: description.value || pipeline.description,
      cover_path: pipeline.coverPath,
      tags: tags.value.split(/[,，]/).filter(Boolean).map((t) => t.trim()),
    }

    const res = await uploadApi.publishAll(data)
    pipeline.completeStep('publish', res.data)
    appendLog('✓ 发布成功！')
    ElMessage.success('发布成功！')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '发布失败'
    appendLog(`✗ 错误：${msg}`)
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('publish', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">选择发布平台，填写描述和话题标签</p>

    <div class="field">
      <p class="field-label">发布平台</p>
      <div class="platform-list">
        <el-checkbox v-model="platforms.douyin">
          <span class="platform-name">抖音</span>
        </el-checkbox>
        <el-checkbox v-model="platforms.xiaohongshu">
          <span class="platform-name">小红书</span>
        </el-checkbox>
        <el-checkbox v-model="platforms.shipinhao">
          <span class="platform-name">视频号</span>
        </el-checkbox>
      </div>
    </div>

    <div class="field">
      <p class="field-label">视频描述</p>
      <el-input
        v-model="description"
        type="textarea"
        :rows="3"
        :placeholder="pipeline.description || '输入视频描述...'"
      />
    </div>

    <div class="field">
      <p class="field-label">话题标签（逗号分隔）</p>
      <el-input
        v-model="tags"
        placeholder="例如：数字人,AI视频,口播"
      />
    </div>

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.publish.loading"
      class="action-btn"
      @click="handlePublish"
    >
      {{ pipeline.steps.publish.loading ? '发布中...' : '一键发布' }}
    </el-button>

    <div v-if="logs.length > 0" class="step-log">
      <p class="result-label">执行日志</p>
      <div ref="logBoxRef" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
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

.platform-list {
  display: flex;
  gap: var(--space-6);
}

.platform-name {
  font-weight: var(--font-medium);
}

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
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

.result-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}
</style>
