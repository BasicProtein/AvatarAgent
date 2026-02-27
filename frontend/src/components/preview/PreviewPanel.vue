<script setup lang="ts">
import { computed } from 'vue'
import { usePipelineStore } from '../../stores/pipeline'

const pipeline = usePipelineStore()

const previewType = computed(() => {
  switch (pipeline.activeStep) {
    case 'extract':
    case 'rewrite':
      return 'text'
    case 'synthesize':
      return 'audio'
    case 'avatar':
    case 'postprod':
      return 'video'
    case 'publish':
      return 'final'
    default:
      return 'text'
  }
})

const previewText = computed(() => {
  return pipeline.rewrittenText || pipeline.extractedText || ''
})

const previewDescription = computed(() => {
  return pipeline.description || ''
})

const videoSrc = computed(() => {
  const path = pipeline.finalVideoPath || pipeline.avatarVideoPath
  if (!path) return ''
  return `http://localhost:8000/output/${path.split(/[/\\]/).pop()}`
})

const coverSrc = computed(() => {
  if (!pipeline.coverPath) return ''
  return `http://localhost:8000/output/${pipeline.coverPath.split(/[/\\]/).pop()}`
})
</script>

<template>
  <div class="preview-panel">
    <div class="preview-header">
      <h3 class="preview-title">预览</h3>
      <span class="preview-step-tag">{{ pipeline.activeStep }}</span>
    </div>

    <div class="phone-frame">
      <div class="phone-dynamic-island" />
      <div class="phone-screen">
        <!-- Text preview -->
        <template v-if="previewType === 'text'">
          <div class="phone-content text-preview" v-if="previewText">
            <div class="phone-avatar">
              <div class="avatar-circle" />
              <span class="avatar-name">数字人口播</span>
            </div>
            <div class="phone-text-body">
              <p class="phone-script">{{ previewText }}</p>
            </div>
            <div class="phone-desc" v-if="previewDescription">
              <p>{{ previewDescription }}</p>
            </div>
          </div>
          <div class="phone-content empty-state" v-else>
            <el-icon :size="40" color="var(--color-text-placeholder)"><VideoCamera /></el-icon>
            <p>等待文案输入...</p>
          </div>
        </template>

        <!-- Video preview -->
        <template v-else-if="previewType === 'video' || previewType === 'final'">
          <div class="phone-content video-preview" v-if="videoSrc">
            <video :src="videoSrc" controls class="phone-video" />
          </div>
          <div class="phone-content empty-state" v-else>
            <el-icon :size="40" color="var(--color-text-placeholder)"><VideoCamera /></el-icon>
            <p>等待视频生成...</p>
          </div>
        </template>

        <!-- Audio preview -->
        <template v-else-if="previewType === 'audio'">
          <div class="phone-content audio-preview">
            <el-icon :size="48" color="var(--color-primary)"><Microphone /></el-icon>
            <p class="audio-label">语音合成</p>
            <p class="audio-hint">合成完成后可在编辑区试听</p>
          </div>
        </template>

        <!-- Bottom bar -->
        <div class="phone-bottom-bar">
          <div class="bottom-icon"><el-icon :size="20"><HomeFilled /></el-icon></div>
          <div class="bottom-icon"><el-icon :size="20"><Search /></el-icon></div>
          <div class="bottom-icon center"><el-icon :size="24"><Plus /></el-icon></div>
          <div class="bottom-icon"><el-icon :size="20"><ChatDotRound /></el-icon></div>
          <div class="bottom-icon"><el-icon :size="20"><User /></el-icon></div>
        </div>
      </div>
      <div class="phone-home-indicator" />
    </div>

    <!-- Cover preview -->
    <div v-if="coverSrc" class="cover-preview">
      <p class="cover-label">封面预览</p>
      <img :src="coverSrc" alt="视频封面" class="cover-img" />
    </div>
  </div>
</template>

<style scoped>
.preview-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-6);
  gap: var(--space-6);
  overflow-y: auto;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  align-self: stretch;
}

.preview-title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.preview-step-tag {
  padding: 2px var(--space-2);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: var(--text-xs);
  border-radius: var(--radius-full);
  font-weight: var(--font-medium);
  text-transform: uppercase;
}

/* Phone frame — iPhone 17 Pro (393×852pt, ~0.46x scale) */
.phone-frame {
  width: 280px;
  background: linear-gradient(145deg, #e8e4df, #d5d0ca);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 40px;
  padding: 4px;
  box-shadow:
    0 2px 8px rgba(0, 0, 0, 0.06),
    0 8px 24px rgba(0, 0, 0, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    inset 0 -1px 0 rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
  position: relative;
}

.phone-dynamic-island {
  width: 72px;
  height: 18px;
  background: #111;
  border-radius: 14px;
  margin: 0 auto;
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
}

/* Camera dot inside Dynamic Island */
.phone-dynamic-island::after {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: radial-gradient(circle, #1a3a5c 30%, #0d1f30 70%);
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.3);
}

.phone-screen {
  width: 100%;
  min-height: 590px;
  background: var(--color-bg-page);
  border-radius: 36px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.phone-content {
  flex: 1;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.empty-state {
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-placeholder);
  font-size: var(--text-sm);
}

/* Text preview */
.phone-avatar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}

.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
}

.avatar-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.phone-text-body {
  flex: 1;
}

.phone-script {
  font-size: var(--text-xs);
  color: var(--color-text-primary);
  line-height: var(--leading-relaxed);
  white-space: pre-wrap;
  display: -webkit-box;
  -webkit-line-clamp: 12;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.phone-desc {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  line-height: var(--leading-relaxed);
}

/* Video preview */
.phone-video {
  width: 100%;
  border-radius: var(--radius-md);
}

/* Audio preview */
.audio-preview {
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.audio-label {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.audio-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* Bottom bar */
.phone-bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
}

.bottom-icon {
  color: var(--color-text-tertiary);
  padding: var(--space-1);
}

.bottom-icon.center {
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
}

.phone-home-indicator {
  width: 100px;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  margin: 6px auto;
}

/* Cover */
.cover-preview {
  align-self: stretch;
}

.cover-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  font-weight: var(--font-medium);
  margin-bottom: var(--space-2);
}

.cover-img {
  width: 100%;
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
</style>
