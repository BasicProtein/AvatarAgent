<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { avatarApi, type AvatarModel, type SavedAvatar } from '../api/avatar'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadRawFile } from 'element-plus'

const models = ref<AvatarModel[]>([])
const savedAvatars = ref<SavedAvatar[]>([])
const loading = ref(false)

// Add avatar form
const avatarName = ref('')
const avatarNameMaxLen = 10
const avatarDesc = ref('')
const avatarDescMaxLen = 200
const savingAvatar = ref(false)
const selectedFile = ref<File | null>(null)
const uploadProgress = ref(0)

onMounted(async () => {
  loading.value = true
  try {
    const [modelsRes, savedRes] = await Promise.all([
      avatarApi.listModels().catch(() => ({ data: [] })),
      avatarApi.listSaved().catch(() => ({ data: [] })),
    ])
    models.value = modelsRes.data
    savedAvatars.value = savedRes.data
  } catch { /* ignore */ }
  finally { loading.value = false }
})

async function refreshModels() {
  try {
    const [modelsRes, savedRes] = await Promise.all([
      avatarApi.listModels(),
      avatarApi.listSaved(),
    ])
    models.value = modelsRes.data
    savedAvatars.value = savedRes.data
    ElMessage.success('已刷新')
  } catch {
    ElMessage.error('刷新失败')
  }
}

function onFileChange(file: UploadFile) {
  selectedFile.value = file.raw as UploadRawFile
}

async function handleSaveAvatar() {
  if (!avatarName.value.trim()) {
    ElMessage.warning('请输入形象名称')
    return
  }
  if (!selectedFile.value) {
    ElMessage.warning('请选择人脸视频文件')
    return
  }
  savingAvatar.value = true
  uploadProgress.value = 0
  try {
    // Step 1: 上传视频，获取服务端路径
    ElMessage.info('上传视频中...')
    const uploadRes = await avatarApi.uploadVideo(selectedFile.value)
    const serverPath = uploadRes.data.path
    uploadProgress.value = 50

    // Step 2: 注册为形象
    await avatarApi.saveAvatar({
      name: avatarName.value.trim(),
      video_path: serverPath,
      description: avatarDesc.value,
    })
    uploadProgress.value = 100

    ElMessage.success(`形象「${avatarName.value}」已保存`)
    // 刷新列表
    const savedRes = await avatarApi.listSaved()
    savedAvatars.value = savedRes.data
    // 清空表单
    avatarName.value = ''
    avatarDesc.value = ''
    selectedFile.value = null
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '保存失败'
    ElMessage.error(msg)
  } finally {
    savingAvatar.value = false
    uploadProgress.value = 0
  }
}

async function handleDeleteAvatar(name: string) {
  try {
    await avatarApi.deleteAvatar(name)
    savedAvatars.value = savedAvatars.value.filter(a => a.name !== name)
    ElMessage.success(`已删除形象「${name}」`)
  } catch {
    ElMessage.error('删除失败')
  }
}

// 合并展示：models 目录中的 + 已保存的自定义形象
const allAvatars = ref<{ name: string; description?: string; tag: string }[]>([])
</script>

<template>
  <div class="page-view">
    <!-- Top: Add Avatar (two columns) -->
    <div class="panel-card add-panel">
      <div class="panel-header">
        <div class="panel-icon">
          <el-icon :size="20"><Plus /></el-icon>
        </div>
        <div class="panel-title-group">
          <h2 class="panel-title">添加形象</h2>
          <p class="panel-subtitle">上传视频文件创建数字人形象</p>
        </div>
      </div>

      <div class="add-content">
        <!-- Left: Video Upload -->
        <div class="upload-col">
          <el-upload
            drag
            action=""
            :auto-upload="false"
            accept=".mp4,.avi,.mov,.wmv,.flv,.mkv,.webm"
            class="video-uploader"
            :on-change="onFileChange"
            :show-file-list="false"
          >
            <div class="upload-inner">
              <el-icon :size="40" color="var(--color-text-placeholder)"><UploadFilled /></el-icon>
              <p class="upload-main-text">
                {{ selectedFile ? selectedFile.name : '点击或拖拽视频文件到此区域' }}
              </p>
              <div class="upload-hints">
                <p>支持 MP4、AVI、MOV、WMV、FLV、MKV、WEBM 格式</p>
                <p>最大 500MB，分辨率建议 720P 或 1080P</p>
                <p>本地模式处理不限制，建议 1080P</p>
                <p>保存后不要变动文件路径，否则会导致生成失败</p>
              </div>
            </div>
          </el-upload>
          <el-progress
            v-if="uploadProgress > 0"
            :percentage="uploadProgress"
            :show-text="false"
            style="margin-top: 8px;"
          />
        </div>

        <!-- Right: Info Form -->
        <div class="form-col">
          <div class="field-group">
            <p class="field-label">形象名称 <span class="required">*</span></p>
            <el-input
              v-model="avatarName"
              :maxlength="avatarNameMaxLen"
              show-word-limit
              placeholder="请输入数字人名称"
              size="large"
            />
          </div>

          <div class="field-group">
            <p class="field-label">描述信息</p>
            <el-input
              v-model="avatarDesc"
              type="textarea"
              :rows="5"
              :maxlength="avatarDescMaxLen"
              show-word-limit
              resize="none"
              placeholder="请输入数字人的描述信息（可选，这里就是为了记忆方便，自己随便填，不填也行，没限制）"
            />
          </div>

          <div class="form-spacer" />

          <el-button
            type="primary"
            size="large"
            class="full-btn"
            :loading="savingAvatar"
            @click="handleSaveAvatar"
          >
            <el-icon v-if="!savingAvatar"><CircleCheck /></el-icon>
            {{ savingAvatar ? '保存中...' : '保存形象' }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- Bottom: Avatar Library -->
    <div class="panel-card library-panel">
      <div class="library-header">
        <div>
          <h2 class="library-title">我的形象库</h2>
          <p class="library-subtitle">管理您创建的所有形象</p>
        </div>
        <el-button size="small" @click="refreshModels">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>

      <!-- 已保存自定义形象 -->
      <div v-if="savedAvatars.length > 0" class="avatar-grid">
        <div
          v-for="avatar in savedAvatars"
          :key="avatar.name"
          class="avatar-card"
        >
          <div class="avatar-thumb">
            <el-icon :size="32" color="var(--color-text-placeholder)"><User /></el-icon>
          </div>
          <div class="avatar-info-bar">
            <h4 class="avatar-name">{{ avatar.name }}</h4>
            <div class="avatar-actions">
              <el-button
                :icon="Delete as any"
                circle size="small" type="danger"
                @click.stop="handleDeleteAvatar(avatar.name)"
              />
            </div>
          </div>
          <div class="avatar-meta">
            <span class="meta-tag">自定义</span>
            <span class="meta-text">{{ avatar.description || avatar.video_path.split(/[/\\]/).pop() }}</span>
          </div>
        </div>
      </div>

      <!-- HeyGem models 目录中的形象 -->
      <div v-if="models.length > 0 && savedAvatars.length === 0" class="avatar-grid">
        <div
          v-for="model in models"
          :key="model.name"
          class="avatar-card"
        >
          <div class="avatar-thumb">
            <el-icon :size="32" color="var(--color-text-placeholder)"><User /></el-icon>
          </div>
          <div class="avatar-info-bar">
            <h4 class="avatar-name">{{ model.name }}</h4>
          </div>
          <div class="avatar-meta">
            <span class="meta-tag">内置</span>
            <span class="meta-text">{{ model.path.split(/[/\\]/).pop() }}</span>
          </div>
        </div>
      </div>

      <div v-if="savedAvatars.length === 0 && models.length === 0" class="library-empty">
        <el-icon :size="40" color="var(--color-text-placeholder)"><User /></el-icon>
        <p>暂无数字人形象，请在上方上传视频并保存</p>
        <p class="empty-hint">也可将模型文件放入 resources/models/ 目录</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Edit, Delete } from '@element-plus/icons-vue'
export default { components: { Edit, Delete } }
</script>

<style scoped>
.page-view {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

/* ===== Panel Card ===== */
.panel-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.panel-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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

/* ===== Add Content: Two Columns ===== */
.add-content {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: var(--space-5);
  align-items: start;
}

/* Upload column */
.upload-col {
  flex: 1;
}

.video-uploader :deep(.el-upload) {
  width: 100%;
}

.video-uploader :deep(.el-upload-dragger) {
  width: 100%;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-page);
  padding: var(--space-10) var(--space-6);
  transition: border-color var(--duration-fast);
}

.video-uploader :deep(.el-upload-dragger:hover) {
  border-color: var(--color-primary);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
}

.upload-main-text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
}

.upload-hints {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.upload-hints p {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-align: center;
  line-height: var(--leading-relaxed);
}

/* Form column */
.form-col {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
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

.required {
  color: var(--color-error);
}

.form-spacer {
  flex: 1;
  min-height: var(--space-4);
}

.full-btn {
  width: 100%;
  height: 44px;
  font-size: var(--text-base) !important;
  font-weight: var(--font-semibold) !important;
}

/* ===== Library ===== */
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

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-4);
}

.avatar-card {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.avatar-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-sm);
}

.avatar-card:hover .avatar-actions {
  opacity: 1;
}

.avatar-thumb {
  width: 100%;
  aspect-ratio: 3 / 4;
  background: var(--color-bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-info-bar {
  display: flex;
  align-items: center;
  padding: var(--space-3) var(--space-3) 0;
}

.avatar-name {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.avatar-actions {
  display: flex;
  gap: 2px;
  opacity: 0;
  transition: opacity var(--duration-fast);
}

.avatar-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3) var(--space-3);
}

.meta-tag {
  font-size: 10px;
  padding: 1px var(--space-2);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  border-radius: var(--radius-full);
  font-weight: var(--font-medium);
}

.meta-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.empty-hint {
  font-size: var(--text-xs);
  color: var(--color-text-placeholder);
}
</style>
