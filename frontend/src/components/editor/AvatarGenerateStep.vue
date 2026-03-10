<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { usePipelineStore } from '../../stores/pipeline'
import { avatarApi, generateAvatarStream, type AvatarModel, type SavedAvatar } from '../../api/avatar'
import { configApi } from '../../api/config'
import { ElMessage } from 'element-plus'

const router = useRouter()

const pipeline = usePipelineStore()

// 引擎 & 模型
const engine = ref<'heygem' | 'tuilionnx'>('heygem')
const heygemModels = ref<AvatarModel[]>([])
const savedAvatars = ref<SavedAvatar[]>([])
const faces = ref<{ id: string; name: string }[]>([])
const selectedModel = ref('')

// TuiliONNX 参数
const batchSize = ref(4)
const syncOffset = ref(0)

// HeyGem 路径配置检测
const heygemPathsMissing = ref(false)

async function checkHeygemPaths() {
  if (engine.value !== 'heygem') return
  try {
    const res = await configApi.getHeygemPaths()
    const { audio_host_dir, video_host_dir } = res.data
    heygemPathsMissing.value = !audio_host_dir || !video_host_dir
  } catch {
    heygemPathsMissing.value = false
  }
}

function goToSettings() {
  router.push('/settings')
}

// 进度日志
const logs = ref<string[]>([])
const logsEl = ref<HTMLElement | null>(null)

let cancelStream: (() => void) | null = null

async function loadModels() {
  try {
    if (engine.value === 'heygem') {
      const [modelsRes, savedRes] = await Promise.all([
        avatarApi.listModels().catch(() => ({ data: [] as AvatarModel[] })),
        avatarApi.listSaved().catch(() => ({ data: [] as SavedAvatar[] })),
      ])
      heygemModels.value = modelsRes.data
      savedAvatars.value = savedRes.data
      // 合并模型列表用于选择：自定义形象优先
      const all = [
        ...savedRes.data.map((a: SavedAvatar) => ({ name: a.name, path: a.video_path })),
        ...modelsRes.data,
      ]
      if (all.length > 0 && !selectedModel.value) selectedModel.value = all[0]!.name
    } else {
      const res = await avatarApi.listFaces().catch(() => ({ data: [] }))
      faces.value = res.data || []
      if (faces.value.length > 0 && !selectedModel.value) selectedModel.value = faces.value[0]!.id
    }
  } catch { /* ignore */ }
}

// 切换引擎时重置模型选择并重新加载，同时检查路径配置
watch(engine, () => {
  selectedModel.value = ''
  loadModels()
  checkHeygemPaths()
})

onMounted(() => {
  loadModels()
  checkHeygemPaths()
})

// 计算当前引擎下的模型选项列表
function modelOptions() {
  if (engine.value === 'heygem') {
    const saved = savedAvatars.value.map(a => ({ name: a.name, label: `${a.name}（自定义）` }))
    const builtin = heygemModels.value
      .filter(m => !savedAvatars.value.some(a => a.name === m.name))
      .map(m => ({ name: m.name, label: m.name }))
    return [...saved, ...builtin]
  }
  return faces.value.map(f => ({ name: f.id, label: f.name || f.id }))
}

async function handleGenerate() {
  if (!pipeline.audioPath) {
    ElMessage.warning('请先完成语音合成')
    return
  }
  if (!selectedModel.value) {
    ElMessage.warning('请选择数字人模型')
    return
  }

  logs.value = []
  pipeline.setStepLoading('avatar', true)

  cancelStream = generateAvatarStream(
    {
      model_name: selectedModel.value,
      audio_path: pipeline.audioPath,
      engine: engine.value,
      batch_size: batchSize.value,
      sync_offset: syncOffset.value,
      add_watermark: false,
    },
    (msg) => {
      logs.value.push(msg)
      // 自动滚动到底部
      setTimeout(() => {
        if (logsEl.value) logsEl.value.scrollTop = logsEl.value.scrollHeight
      }, 0)
    },
    (videoPath) => {
      pipeline.avatarVideoPath = videoPath
      pipeline.completeStep('avatar', { video_path: videoPath })
      pipeline.setActiveStep('postprod')
      pipeline.setStepLoading('avatar', false)
      ElMessage.success('数字人视频生成成功')
      cancelStream = null
    },
    (errMsg) => {
      ElMessage.error(errMsg)
      pipeline.setStepLoading('avatar', false)
      cancelStream = null
    },
  )
}

function handleCancel() {
  cancelStream?.()
  cancelStream = null
  pipeline.setStepLoading('avatar', false)
  ElMessage.info('已取消生成')
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">选择数字人模型和引擎，生成口播视频</p>

    <!-- HeyGem 路径未配置提示 -->
    <div v-if="engine === 'heygem' && heygemPathsMissing" class="config-notice">
      <div class="config-notice-icon">⚠️</div>
      <div class="config-notice-body">
        <p class="config-notice-title">HeyGem Docker 路径尚未配置</p>
        <p class="config-notice-desc">提交任务时需要将本机文件路径映射为容器内路径，否则 HeyGem 服务会返回 404 找不到文件。</p>
      </div>
      <el-button size="small" type="primary" plain @click="goToSettings">去设置</el-button>
    </div>

    <div class="field">
      <p class="field-label">数字人引擎</p>
      <el-radio-group v-model="engine" :disabled="pipeline.steps.avatar.loading">
        <el-radio-button value="heygem">HeyGem</el-radio-button>
        <el-radio-button value="tuilionnx">TuiliONNX</el-radio-button>
      </el-radio-group>
    </div>

    <div class="field">
      <p class="field-label">选择模型</p>
      <el-select
        v-model="selectedModel"
        placeholder="选择数字人模型"
        style="width: 100%;"
        size="large"
        :disabled="pipeline.steps.avatar.loading"
      >
        <el-option
          v-for="opt in modelOptions()"
          :key="opt.name"
          :label="opt.label"
          :value="opt.name"
        />
        <el-option v-if="modelOptions().length === 0" label="暂无模型" value="" disabled />
      </el-select>
    </div>

    <div v-if="engine === 'tuilionnx'" class="params-row">
      <div class="field" style="flex: 1;">
        <p class="field-label">批次大小</p>
        <el-input-number v-model="batchSize" :min="1" :max="16" size="default" :disabled="pipeline.steps.avatar.loading" />
      </div>
      <div class="field" style="flex: 1;">
        <p class="field-label">同步偏移</p>
        <el-input-number v-model="syncOffset" :min="-10" :max="10" size="default" :disabled="pipeline.steps.avatar.loading" />
      </div>
    </div>

    <div class="btn-row">
      <el-button
        type="primary"
        size="large"
        :loading="pipeline.steps.avatar.loading"
        class="action-btn"
        @click="handleGenerate"
      >
        {{ pipeline.steps.avatar.loading ? '生成中...' : '生成视频' }}
      </el-button>
      <el-button
        v-if="pipeline.steps.avatar.loading"
        size="large"
        @click="handleCancel"
      >
        取消
      </el-button>
    </div>

    <!-- 进度日志 -->
    <div v-if="logs.length > 0" class="step-log">
      <p class="result-label">执行日志</p>
      <div ref="logsEl" class="log-box">
        <p v-for="(line, i) in logs" :key="i" class="log-line">{{ line }}</p>
      </div>
    </div>

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

.btn-row {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.action-btn {
  padding: 0 var(--space-6) !important;
}

/* 进度日志框 */
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
  white-space: pre-wrap;
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

/* 路径未配置提示 */
.config-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: rgba(243, 156, 18, 0.06);
  border: 1px solid rgba(243, 156, 18, 0.35);
  border-radius: var(--radius-md);
}
.config-notice-icon {
  font-size: 16px;
  flex-shrink: 0;
  line-height: 1.5;
}
.config-notice-body {
  flex: 1;
  min-width: 0;
}
.config-notice-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: #b7860b;
  margin-bottom: 2px;
}
.config-notice-desc {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
