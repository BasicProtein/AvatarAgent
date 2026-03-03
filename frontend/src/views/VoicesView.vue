<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { audioApi, type VoiceItem } from '../api/audio'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadRawFile } from 'element-plus'

const voices = ref<VoiceItem[]>([])
const loading = ref(false)

// Training section
const trainTab = ref<'upload' | 'record'>('upload')
const voiceName = ref('')
const voiceNameMaxLen = 10
const trainingLoading = ref(false)
const selectedAudioFile = ref<File | null>(null)

// ─── Recording states ───
const isRecording = ref(false)
const recordDuration = ref(0)          // seconds
const recordedBlob = ref<Blob | null>(null)
const recordPreviewUrl = ref('')
let mediaRecorder: MediaRecorder | null = null
let recordingChunks: Blob[] = []
let recordTimer: ReturnType<typeof setInterval> | null = null

// Synthesis section
const selectedVoiceIdx = ref(0)
const synthText = ref('')
const synthTextMaxLen = 5000
const synthSpeed = ref(50)
const synthEmotion = ref('')
const synthLoading = ref(false)
const synthAudioUrl = ref('')

const emotionOptions = [
  { label: '默认', value: '' },
  { label: '开心', value: 'happy' },
  { label: '悲伤', value: 'sad' },
  { label: '愤怒', value: 'angry' },
  { label: '平静', value: 'calm' },
]

const speedValue = computed(() => (synthSpeed.value / 50).toFixed(1))

/** 格式化录音时长 mm:ss */
const formattedDuration = computed(() => {
  const m = Math.floor(recordDuration.value / 60)
  const s = recordDuration.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

onMounted(async () => {
  loading.value = true
  try {
    const res = await audioApi.listVoices()
    voices.value = res.data
  } catch { /* ignore */ }
  finally { loading.value = false }
})

onBeforeUnmount(() => {
  // 离开页面时清理录音资源
  stopRecordingCleanup()
  if (recordPreviewUrl.value) URL.revokeObjectURL(recordPreviewUrl.value)
})

async function refreshVoices() {
  try {
    const res = await audioApi.listVoices()
    voices.value = res.data
    ElMessage.success('已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

function onAudioFileChange(file: UploadFile) {
  selectedAudioFile.value = file.raw as UploadRawFile
}

// ─── Recording functions ───

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })

    // 优先使用 wav，fallback webm
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    mediaRecorder = new MediaRecorder(stream, { mimeType })
    recordingChunks = []
    recordDuration.value = 0
    recordedBlob.value = null
    if (recordPreviewUrl.value) {
      URL.revokeObjectURL(recordPreviewUrl.value)
      recordPreviewUrl.value = ''
    }

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordingChunks.push(e.data)
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordingChunks, { type: mimeType })
      recordedBlob.value = blob
      recordPreviewUrl.value = URL.createObjectURL(blob)

      // 将 Blob 转为 File，供 handleTrain 使用
      const ext = mimeType.includes('webm') ? 'webm' : 'wav'
      const file = new File([blob], `recording_${Date.now()}.${ext}`, { type: mimeType })
      selectedAudioFile.value = file

      // 释放麦克风
      stream.getTracks().forEach(t => t.stop())
    }

    mediaRecorder.start(250) // 每 250ms 生成一个 chunk
    isRecording.value = true

    // 计时器
    recordTimer = setInterval(() => {
      recordDuration.value++
      // 最长 60 秒自动停止
      if (recordDuration.value >= 60) {
        stopRecording()
      }
    }, 1000)

    ElMessage.success('开始录音，请朗读一段话...')
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : '未知错误'
    if (msg.includes('Permission') || msg.includes('NotAllowed')) {
      ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风')
    } else {
      ElMessage.error(`无法启动录音: ${msg}`)
    }
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  isRecording.value = false
  if (recordTimer) {
    clearInterval(recordTimer)
    recordTimer = null
  }
}

function stopRecordingCleanup() {
  stopRecording()
  if (mediaRecorder) {
    // 释放可能残留的 stream
    try {
      mediaRecorder.stream?.getTracks().forEach(t => t.stop())
    } catch { /* ignore */ }
    mediaRecorder = null
  }
}

function discardRecording() {
  recordedBlob.value = null
  if (recordPreviewUrl.value) {
    URL.revokeObjectURL(recordPreviewUrl.value)
    recordPreviewUrl.value = ''
  }
  selectedAudioFile.value = null
  recordDuration.value = 0
}

// ─── Train (supports both upload & record) ───

async function handleTrain() {
  if (!voiceName.value.trim()) {
    ElMessage.warning('请输入声音名称')
    return
  }
  if (!selectedAudioFile.value) {
    if (trainTab.value === 'record') {
      ElMessage.warning('请先录制一段音频')
    } else {
      ElMessage.warning('请选择参考音频文件')
    }
    return
  }
  trainingLoading.value = true
  try {
    // Step 1: 上传参考音频
    ElMessage.info('上传音频中...')
    const uploadRes = await audioApi.uploadSample(selectedAudioFile.value)
    const serverPath = uploadRes.data.path

    // Step 2: 注册为音色
    await audioApi.trainVoice({
      name: voiceName.value.trim(),
      audio_path: serverPath,
    })

    ElMessage.success(`音色「${voiceName.value}」训练完成`)
    // 刷新音色列表
    const res = await audioApi.listVoices()
    voices.value = res.data
    // 清空表单
    voiceName.value = ''
    selectedAudioFile.value = null
    discardRecording()
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '训练失败'
    ElMessage.error(msg)
  } finally {
    trainingLoading.value = false
  }
}

async function handleSynthesize() {
  if (!synthText.value.trim()) {
    ElMessage.warning('请输入合成文本')
    return
  }
  if (voices.value.length === 0) {
    ElMessage.warning('请先选择声音模型')
    return
  }
  synthLoading.value = true
  try {
    const res = await audioApi.synthesize({
      text: synthText.value,
      voice_id: selectedVoiceIdx.value,
      speed: Number(speedValue.value),
    })
    const blob = new Blob([res.data], { type: 'audio/wav' })
    synthAudioUrl.value = URL.createObjectURL(blob)
    ElMessage.success('语音生成成功')
  } catch {
    ElMessage.error('语音生成失败')
  } finally {
    synthLoading.value = false
  }
}
</script>

<template>
  <div class="page-view">
    <!-- Top: Two-column cards -->
    <div class="top-row">
      <!-- Left: Voice Training -->
      <div class="panel-card">
        <div class="panel-header">
          <div class="panel-icon training">
            <el-icon :size="20"><Microphone /></el-icon>
          </div>
          <div class="panel-title-group">
            <h2 class="panel-title">声音训练</h2>
            <p class="panel-subtitle">上传音频样本，训练专属声音模型</p>
          </div>
        </div>

        <!-- Tab switch -->
        <div class="tab-switch">
          <button
            class="tab-btn"
            :class="{ active: trainTab === 'upload' }"
            @click="trainTab = 'upload'"
          >上传音频</button>
          <button
            class="tab-btn"
            :class="{ active: trainTab === 'record' }"
            @click="trainTab = 'record'"
          >直接录音</button>
        </div>

        <!-- Upload area -->
        <div v-if="trainTab === 'upload'" class="upload-area">
          <el-upload
            drag
            action=""
            :auto-upload="false"
            accept=".mp3,.wav,.m4a,.flac"
            :on-change="onAudioFileChange"
            :show-file-list="false"
          >
            <div class="upload-inner">
              <el-icon :size="36" color="var(--color-text-placeholder)"><Upload /></el-icon>
              <p class="upload-main-text">
                {{ selectedAudioFile ? selectedAudioFile.name : '点击或拖拽音频文件到此区域' }}
              </p>
              <p class="upload-hint">支持 MP3、WAV、M4A 等格式</p>
              <p class="upload-hint">建议时长 5-30 秒，文件大小不超过 50MB</p>
            </div>
          </el-upload>
        </div>

        <!-- Record area -->
        <div v-else class="record-area">
          <div class="record-placeholder">
            <!-- idle -->
            <template v-if="!isRecording && !recordedBlob">
              <el-icon :size="36" color="var(--color-primary)"><Microphone /></el-icon>
              <p>点击下方按钮开始录音</p>
              <el-button type="primary" round @click="startRecording">
                <el-icon><VideoPlay /></el-icon>
                开始录音
              </el-button>
              <p class="record-sub-hint">建议在安静环境下录制 5-30 秒清晰人声</p>
            </template>

            <!-- recording in progress -->
            <template v-else-if="isRecording">
              <div class="recording-indicator">
                <span class="pulse-dot" />
                <span class="recording-label">录音中</span>
                <span class="recording-timer">{{ formattedDuration }}</span>
              </div>
              <div class="waveform">
                <span v-for="i in 20" :key="i" class="wave-bar" :style="{ animationDelay: `${i * 0.06}s` }" />
              </div>
              <el-button type="danger" round @click="stopRecording">
                <el-icon><VideoPause /></el-icon>
                停止录音
              </el-button>
              <p class="record-sub-hint">最长 60 秒，点击停止结束录音</p>
            </template>

            <!-- recording done -->
            <template v-else-if="recordedBlob">
              <el-icon :size="36" color="var(--color-success)"><CircleCheck /></el-icon>
              <p>录音完成（{{ formattedDuration }}）</p>
              <audio v-if="recordPreviewUrl" :src="recordPreviewUrl" controls class="preview-audio" />
              <el-button round @click="discardRecording">
                <el-icon><RefreshRight /></el-icon>
                重新录制
              </el-button>
            </template>
          </div>
        </div>

        <!-- Voice name input -->
        <div class="voice-name-section">
          <p class="field-label">声音名称</p>
          <el-input
            v-model="voiceName"
            :maxlength="voiceNameMaxLen"
            show-word-limit
            placeholder="为这个声音起个名字"
            size="large"
          >
            <template #prefix>
              <el-icon><Edit /></el-icon>
            </template>
          </el-input>
          <p class="field-hint">起个名字方便记忆（{{ voiceNameMaxLen }}个字以内），例如：我的声音</p>
        </div>

        <!-- Train button -->
        <el-button
          type="primary"
          size="large"
          class="full-btn"
          :loading="trainingLoading"
          @click="handleTrain"
        >
          <el-icon v-if="!trainingLoading"><Upload /></el-icon>
          {{ trainingLoading ? '训练中...' : '开始训练' }}
        </el-button>
        <p class="btn-hint" v-if="!voiceName.trim() || trainTab === 'upload'">
          <span v-if="!voiceName.trim()">请输入声音名称</span>
          <span v-else>请上传或录制音频</span>
        </p>
      </div>

      <!-- Right: Voice Synthesis -->
      <div class="panel-card">
        <div class="panel-header">
          <div class="panel-icon synthesis">
            <el-icon :size="20"><Headset /></el-icon>
          </div>
          <div class="panel-title-group">
            <h2 class="panel-title">声音合成</h2>
            <p class="panel-subtitle">选择声音模型，生成个性化语音</p>
          </div>
        </div>

        <!-- Voice model select -->
        <div class="field-group">
          <p class="field-label">选择声音模型</p>
          <el-select
            v-model="selectedVoiceIdx"
            placeholder="选择声音模型"
            style="width: 100%;"
            size="large"
          >
            <el-option
              v-for="(voice, idx) in voices"
              :key="idx"
              :label="voice.name"
              :value="idx"
            />
            <el-option
              v-if="voices.length === 0"
              label="暂无模型（请先训练声音）"
              :value="0"
              disabled
            />
          </el-select>
        </div>

        <!-- Text input -->
        <div class="field-group">
          <p class="field-label">输入文本</p>
          <el-input
            v-model="synthText"
            type="textarea"
            :rows="5"
            :maxlength="synthTextMaxLen"
            show-word-limit
            placeholder="你好，这是一个声音克隆测试。"
            resize="none"
          />
        </div>

        <!-- Speed & Emotion row -->
        <div class="params-row">
          <div class="param-item speed-param">
            <p class="field-label">语速</p>
            <el-slider
              v-model="synthSpeed"
              :min="25"
              :max="100"
              :show-tooltip="false"
            />
            <span class="speed-value">{{ speedValue }}x</span>
          </div>
          <div class="param-item">
            <p class="field-label">情绪类型</p>
            <div class="emotion-row">
              <el-select
                v-model="synthEmotion"
                placeholder="选择情绪（可选）"
                clearable
                size="default"
                style="flex: 1;"
              >
                <el-option
                  v-for="opt in emotionOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <el-input-number
                v-model="synthSpeed"
                :min="25"
                :max="100"
                :step="5"
                size="default"
                style="width: 90px;"
                controls-position="right"
              />
            </div>
          </div>
        </div>

        <!-- Synthesize button -->
        <el-button
          type="primary"
          size="large"
          class="full-btn"
          :loading="synthLoading"
          @click="handleSynthesize"
        >
          <el-icon v-if="!synthLoading"><Headset /></el-icon>
          {{ synthLoading ? '生成中...' : '生成语音' }}
        </el-button>
        <p class="btn-hint" v-if="voices.length === 0">请先选择声音模型</p>

        <!-- Audio playback -->
        <div v-if="synthAudioUrl" class="audio-result">
          <audio :src="synthAudioUrl" controls style="width: 100%;" />
        </div>
      </div>
    </div>

    <!-- Bottom: Voice Library -->
    <div class="library-section">
      <div class="library-header">
        <div>
          <h2 class="library-title">我的声音库</h2>
          <p class="library-subtitle">管理您训练的所有声音模型</p>
        </div>
        <el-button size="small" @click="refreshVoices">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <div v-if="voices.length > 0" class="library-grid">
        <div
          v-for="(voice, idx) in voices"
          :key="voice.name"
          class="voice-library-card"
          :class="{ selected: selectedVoiceIdx === idx }"
          @click="selectedVoiceIdx = idx"
        >
          <div class="vlc-top">
            <div class="vlc-icon">
              <el-icon :size="16"><Microphone /></el-icon>
            </div>
            <h4 class="vlc-name">{{ voice.name }}</h4>
            <div class="vlc-actions">
              <el-button :icon="VideoPlay as any" circle size="small" />
              <el-button :icon="Edit as any" circle size="small" />
              <el-button :icon="Delete as any" circle size="small" type="danger" />
            </div>
          </div>
          <p class="vlc-path">{{ voice.path }}</p>
          <div class="vlc-meta">
            <span class="vlc-tag">已就绪</span>
          </div>
        </div>
      </div>

      <div v-else class="library-empty">
        <el-icon :size="40" color="var(--color-text-placeholder)"><Microphone /></el-icon>
        <p>暂无训练好的声音，请在上方训练区域上传音频并开始训练</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { VideoPlay, Edit, Delete } from '@element-plus/icons-vue'
export default { components: { VideoPlay, Edit, Delete } }
</script>

<style scoped>
.page-view {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
}

/* ===== Top Row: Two Panels ===== */
.top-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  margin-bottom: var(--space-6);
}

.panel-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.panel-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.panel-icon.training {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.panel-icon.synthesis {
  background: rgba(92, 140, 202, 0.1);
  color: var(--color-info);
}

.panel-title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.panel-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 1px;
}

/* ===== Tab Switch ===== */
.tab-switch {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border-light);
}

.tab-btn {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-tertiary);
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all var(--duration-fast) var(--ease-out);
}

.tab-btn:hover {
  color: var(--color-text-primary);
}

.tab-btn.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* ===== Upload & Record ===== */
.upload-area :deep(.el-upload-dragger) {
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-page);
  padding: var(--space-8) var(--space-4);
  transition: border-color var(--duration-fast);
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary);
}

.upload-area :deep(.el-upload) {
  width: 100%;
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.upload-main-text {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.upload-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* ===== Record Area — Claude 风格 ===== */
.record-area {
  border: 1px solid rgba(31, 30, 29, 0.12);
  border-radius: 12px;
  background: rgba(250, 249, 245, 0.6);
  padding: var(--space-8) var(--space-6);
  min-height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 统一的 placeholder 容器 — 居中纵向排列 */
.record-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.record-placeholder p {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: 400;
  margin: 0;
}

.record-sub-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-align: center;
  line-height: 1.5;
}

/* ── 录音进行中 ── */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #C0392B;
  animation: pulse-glow 1.2s ease-in-out infinite;
  flex-shrink: 0;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.75); }
}

.recording-label {
  font-size: 13px;
  font-weight: 500;
  color: #C0392B;
  letter-spacing: 0.01em;
}

.recording-timer {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  margin-left: var(--space-1);
  letter-spacing: 0.05em;
}

/* 波形动画 */
.waveform {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2.5px;
  height: 36px;
  padding: 0 var(--space-2);
}

.wave-bar {
  width: 2.5px;
  border-radius: 2px;
  background: var(--color-primary);
  opacity: 0.7;
  animation: wave-bounce 0.9s ease-in-out infinite alternate;
}

@keyframes wave-bounce {
  0%   { height: 4px;  opacity: 0.3; }
  100% { height: 28px; opacity: 0.85; }
}

/* ── 录音完成 ── */
.preview-audio {
  width: 100%;
  max-width: 320px;
  border-radius: 10px;
  height: 36px;
}


/* ===== Voice Name ===== */
.voice-name-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.field-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.field-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* ===== Full-width button ===== */
.full-btn {
  width: 100%;
  height: 44px;
  font-size: var(--text-base) !important;
  font-weight: var(--font-semibold) !important;
}

.btn-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-align: center;
}

/* ===== Params Row ===== */
.params-row {
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: var(--space-4);
  align-items: start;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.speed-param {
  position: relative;
}

.speed-value {
  position: absolute;
  right: 0;
  top: 0;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.emotion-row {
  display: flex;
  gap: var(--space-2);
}

.audio-result {
  background: var(--color-bg-hover);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

/* ===== Bottom: Library ===== */
.library-section {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-5);
}

.library-title {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.library-subtitle {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
}

.voice-library-card {
  padding: var(--space-4);
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.voice-library-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.voice-library-card.selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary-bg);
}

.vlc-top {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.vlc-icon {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.vlc-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.vlc-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast);
}

.voice-library-card:hover .vlc-actions {
  opacity: 1;
}

.vlc-path {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.vlc-meta {
  display: flex;
  gap: var(--space-2);
}

.vlc-tag {
  font-size: 10px;
  padding: 1px var(--space-2);
  background: rgba(76, 175, 80, 0.1);
  color: var(--color-success);
  border-radius: var(--radius-full);
  font-weight: var(--font-medium);
}

.library-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-10) 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
