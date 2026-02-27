<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { avatarApi, type AvatarModel } from '../../api/avatar'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const models = ref<AvatarModel[]>([])
const selectedModel = ref('')
const engine = ref<'tuilionnx' | 'heygem'>('tuilionnx')
const batchSize = ref(4)
const syncOffset = ref(0)

onMounted(async () => {
  try {
    const res = await avatarApi.listModels()
    models.value = res.data
    if (models.value.length > 0) selectedModel.value = models.value[0]!.name
  } catch { /* ignore */ }
})

async function handleGenerate() {
  if (!pipeline.audioPath) {
    ElMessage.warning('请先完成语音合成')
    return
  }
  if (!selectedModel.value) {
    ElMessage.warning('请选择数字人模型')
    return
  }
  pipeline.setStepLoading('avatar', true)
  try {
    const res = await avatarApi.generate({
      model_name: selectedModel.value,
      audio_path: pipeline.audioPath,
      engine: engine.value,
      batch_size: batchSize.value,
      sync_offset: syncOffset.value,
    })
    pipeline.avatarVideoPath = (res.data as Record<string, string>).video_path || ''
    pipeline.completeStep('avatar', res.data as Record<string, unknown>)
    pipeline.setActiveStep('postprod')
    ElMessage.success('数字人视频生成成功')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '生成失败'
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('avatar', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">选择数字人模型和引擎，生成口播视频</p>

    <div class="field">
      <p class="field-label">数字人引擎</p>
      <el-radio-group v-model="engine">
        <el-radio-button value="tuilionnx">TuiliONNX</el-radio-button>
        <el-radio-button value="heygem">HeyGem</el-radio-button>
      </el-radio-group>
    </div>

    <div class="field">
      <p class="field-label">选择模型</p>
      <el-select v-model="selectedModel" placeholder="选择数字人模型" style="width: 100%;" size="large">
        <el-option
          v-for="model in models"
          :key="model.name"
          :label="model.name"
          :value="model.name"
        />
        <el-option v-if="models.length === 0" label="暂无模型" value="" disabled />
      </el-select>
    </div>

    <div class="params-row">
      <div class="field" style="flex: 1;">
        <p class="field-label">批次大小</p>
        <el-input-number v-model="batchSize" :min="1" :max="16" size="default" />
      </div>
      <div class="field" style="flex: 1;">
        <p class="field-label">同步偏移</p>
        <el-input-number v-model="syncOffset" :min="-10" :max="10" size="default" />
      </div>
    </div>

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.avatar.loading"
      class="action-btn"
      @click="handleGenerate"
    >
      {{ pipeline.steps.avatar.loading ? '生成中...' : '生成视频' }}
    </el-button>

    <div v-if="pipeline.avatarVideoPath" class="result-preview">
      <p class="result-label">生成完成</p>
      <p class="result-path">{{ pipeline.avatarVideoPath }}</p>
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

.params-row {
  display: flex;
  gap: var(--space-4);
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
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.result-path {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}
</style>
