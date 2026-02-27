<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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

// Cover settings
const coverText = ref('')
const useAiCover = ref(false)

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
  pipeline.setStepLoading('postprod', true)
  try {
    // Step 1: Add subtitle
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

    // Step 2: Add BGM (optional)
    if (!skipBgm.value) {
      const bgmRes = await videoApi.addBgm({
        video_path: currentVideo,
        bgm_name: selectedBgm.value || undefined,
        volume: bgmVolume.value,
      })
      currentVideo = bgmRes.data.video_path
    }

    // Step 3: Generate cover
    const coverRes = await videoApi.generateCover({
      video_path: currentVideo,
      text: coverText.value,
      use_ai: useAiCover.value,
      api_key: apiKey.value,
    })

    pipeline.finalVideoPath = currentVideo
    pipeline.coverPath = coverRes.data.cover_path
    pipeline.completeStep('postprod')
    pipeline.setActiveStep('publish')
    ElMessage.success('视频后期处理完成')
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '后期处理失败'
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
          <el-select v-model="selectedBgm" placeholder="随机选择" clearable style="width: 100%;" size="default">
            <el-option v-for="b in bgmList" :key="b.name" :label="b.name" :value="b.name" />
          </el-select>
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

.action-btn {
  align-self: flex-start;
  padding: 0 var(--space-6) !important;
}
</style>
