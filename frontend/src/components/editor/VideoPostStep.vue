<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'
import { useConfigStore } from '../../stores/config'
import { videoApi } from '../../api/video'
import { ElMessage } from 'element-plus'

const pipeline = usePipelineStore()
const config = useConfigStore()
const fonts = ref<string[]>([])
const bgmList = ref<Array<{ name: string; path: string }>>([])

// Subtitle settings
const subtitleFont = ref('Microsoft YaHei')
const subtitleSize = ref(11)
const subtitleColor = ref('#FFFFFF')
const outlineColor = ref('#000000')

// BGM settings
const selectedBgm = ref('')
const bgmVolume = ref(0.5)
const skipBgm = ref(false)
const bgmUploading = ref(false)

async function handleBgmUpload(file: File) {
  bgmUploading.value = true
  try {
    const res = await videoApi.uploadBgm(file)
    bgmList.value.push({ name: res.data.name, path: res.data.path })
    selectedBgm.value = res.data.name
    ElMessage.success(`BGM "${res.data.name}" 上传成功`)
  } catch {
    ElMessage.error('BGM 上传失败')
  } finally {
    bgmUploading.value = false
  }
}

// Cover settings
const coverText = ref('')
const useAiCover = ref(false)

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

onMounted(async () => {
  try {
    const [fontsRes, bgmRes] = await Promise.all([
      videoApi.listFonts(),
      videoApi.listBgm(),
    ])
    fonts.value = fontsRes.data.fonts
    bgmList.value = bgmRes.data.bgm_list
  } catch { /* ignore */ }
})

const videoPath = computed(() => pipeline.avatarVideoPath)
const apiKey = computed(() => config.apiKeys[0] || '')

async function handlePostProd() {
  if (!videoPath.value) {
    ElMessage.warning('请先生成数字人视频')
    return
  }
  logs.value = []
  pipeline.setStepLoading('postprod', true)
  appendLog('开始视频后期处理...')
  try {
    // Step 1: Add subtitle
    appendLog('步骤 1/3：添加字幕...')
    const subRes = await videoApi.addSubtitle({
      video_path: videoPath.value,
      text: pipeline.rewrittenText || pipeline.extractedText,
      api_key: apiKey.value,
      style: {
        font_family: subtitleFont.value,
        font_size: subtitleSize.value,
        font_color: subtitleColor.value,
        outline_color: outlineColor.value,
        bottom_margin: 60,
      },
    })
    let currentVideo = subRes.data.video_path
    appendLog('✓ 字幕添加完成')

    // Step 2: Add BGM (optional)
    if (!skipBgm.value) {
      appendLog('步骤 2/3：添加背景音乐...')
      const bgmRes = await videoApi.addBgm({
        video_path: currentVideo,
        bgm_name: selectedBgm.value || undefined,
        volume: bgmVolume.value,
      })
      currentVideo = bgmRes.data.video_path
      appendLog('✓ 背景音乐添加完成')
    } else {
      appendLog('步骤 2/3：跳过背景音乐')
    }

    // Step 3: Generate cover
    appendLog('步骤 3/3：生成封面...')
    const coverRes = await videoApi.generateCover({
      video_path: currentVideo,
      text: coverText.value,
      script_text: pipeline.rewrittenText || pipeline.extractedText,
      use_ai: useAiCover.value,
      api_key: apiKey.value,
    })

    pipeline.finalVideoPath = currentVideo
    pipeline.coverPath = coverRes.data.cover_path
    pipeline.completeStep('postprod')
    pipeline.setActiveStep('publish')
    appendLog('✓ 后期处理全部完成')
    ElMessage.success('视频后期处理完成')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '后期处理失败'
    appendLog(`✗ 错误：${msg}`)
    ElMessage.error(msg)
  } finally {
    pipeline.setStepLoading('postprod', false)
  }
}
</script>

<template>
  <div class="step-content">
    <p class="step-desc">添加字幕、背景音乐、生成封面</p>

    <!-- Subtitle section -->
    <div class="sub-section">
      <h4 class="sub-title">
        <el-icon><Tickets /></el-icon>
        字幕设置
      </h4>
      <div class="form-grid">
        <div class="field">
          <p class="field-label">字体</p>
          <el-select v-model="subtitleFont" size="default" style="width: 100%;">
            <el-option v-for="f in fonts" :key="f" :label="f" :value="f" />
          </el-select>
        </div>
        <div class="field">
          <p class="field-label">字号</p>
          <el-input-number v-model="subtitleSize" :min="8" :max="30" size="default" />
        </div>
        <div class="field">
          <p class="field-label">字幕颜色</p>
          <el-color-picker v-model="subtitleColor" size="default" />
        </div>
        <div class="field">
          <p class="field-label">描边颜色</p>
          <el-color-picker v-model="outlineColor" size="default" />
        </div>
      </div>
    </div>

    <!-- BGM section -->
    <div class="sub-section">
      <h4 class="sub-title">
        <el-icon><Headset /></el-icon>
        背景音乐
      </h4>
      <el-checkbox v-model="skipBgm">不添加 BGM</el-checkbox>
      <template v-if="!skipBgm">
        <div class="field">
          <div class="bgm-select-row">
            <el-select v-model="selectedBgm" placeholder="随机选择" clearable style="flex: 1;" size="default">
              <el-option v-for="b in bgmList" :key="b.name" :label="b.name" :value="b.name" />
            </el-select>
            <el-upload
              :show-file-list="false"
              accept=".mp3,.wav,.flac,.aac,.m4a"
              :before-upload="(file: File) => { handleBgmUpload(file); return false }"
            >
              <el-button size="default" :loading="bgmUploading" plain>上传</el-button>
            </el-upload>
          </div>
        </div>
        <div class="field">
          <p class="field-label">音量 ({{ (bgmVolume * 100).toFixed(0) }}%)</p>
          <el-slider v-model="bgmVolume" :min="0" :max="1" :step="0.05" :show-tooltip="false" />
        </div>
      </template>
    </div>

    <!-- Cover section -->
    <div class="sub-section">
      <h4 class="sub-title">
        <el-icon><Picture /></el-icon>
        封面生成
      </h4>
      <el-checkbox v-model="useAiCover">使用 AI 自动生成封面文案</el-checkbox>
      <el-input
        v-if="!useAiCover"
        v-model="coverText"
        placeholder="输入封面文案..."
        type="textarea"
        :rows="2"
      />
    </div>

    <el-button
      type="primary"
      size="large"
      :loading="pipeline.steps.postprod.loading"
      class="action-btn"
      @click="handlePostProd"
    >
      {{ pipeline.steps.postprod.loading ? '处理中...' : '开始后期处理' }}
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

.sub-section {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.sub-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.field {
  display: flex;
  flex-direction: column;
}

.field-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  margin-bottom: var(--space-1);
}

.bgm-select-row {
  display: flex;
  gap: var(--space-2);
  align-items: center;
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
