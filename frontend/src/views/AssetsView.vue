<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

// Categories
interface Category {
  id: string
  name: string
  count: number
}

const categories = ref<Category[]>([
  { id: 'all', name: '全部素材', count: 0 },
])
const activeCategory = ref('all')
const newCatName = ref('')
const showNewCat = ref(false)

// Assets
interface AssetItem {
  id: string
  name: string
  type: 'video' | 'image'
  category: string
  size: string
  date: string
  thumb: string
}

const assets = ref<AssetItem[]>([])
const searchQuery = ref('')
const selectedIds = ref<string[]>([])
const showUploadPanel = ref(false)
const uploadCategory = ref('all')

const filteredAssets = computed(() => {
  let list = assets.value
  if (activeCategory.value !== 'all') {
    list = list.filter(a => a.category === activeCategory.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q))
  }
  return list
})

const isAllSelected = computed(() =>
  filteredAssets.value.length > 0 && selectedIds.value.length === filteredAssets.value.length
)

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = filteredAssets.value.map(a => a.id)
  }
}

function addCategory() {
  if (!newCatName.value.trim()) return
  categories.value.push({
    id: Date.now().toString(),
    name: newCatName.value.trim(),
    count: 0,
  })
  newCatName.value = ''
  showNewCat.value = false
  ElMessage.success('分类已创建')
}

function openUpload() {
  showUploadPanel.value = true
}
</script>

<template>
  <div class="page-view">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">素材管理</h1>
        <p class="page-desc">管理视频素材的分类、上传、标记和向量化</p>
      </div>
      <div class="header-right">
        <el-button @click="showNewCat = true">
          <el-icon><Plus /></el-icon>
          新建分类
        </el-button>
        <el-button type="primary" @click="openUpload">
          <el-icon><Upload /></el-icon>
          上传视频/图片
        </el-button>
        <el-input
          v-model="searchQuery"
          placeholder="搜索素材..."
          clearable
          style="width: 200px;"
          size="default"
        >
          <template #suffix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- Main Content: Category Sidebar + Asset Grid -->
    <div class="main-content">
      <!-- Left: Category Sidebar -->
      <div class="category-sidebar">
        <div class="sidebar-header">
          <h3 class="sidebar-title">分类管理</h3>
          <el-button size="small" circle :icon="Refresh as any" @click="() => {}" />
        </div>

        <div class="category-list">
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="category-item"
            :class="{ active: activeCategory === cat.id }"
            @click="activeCategory = cat.id"
          >
            <span class="cat-name">{{ cat.name }}</span>
            <span class="cat-count">{{ cat.count }}</span>
          </div>
        </div>

        <!-- New category input -->
        <div v-if="showNewCat" class="new-cat-form">
          <el-input
            v-model="newCatName"
            placeholder="分类名称"
            size="small"
            @keyup.enter="addCategory"
          />
          <div class="new-cat-btns">
            <el-button size="small" @click="showNewCat = false">取消</el-button>
            <el-button size="small" type="primary" @click="addCategory">确定</el-button>
          </div>
        </div>
      </div>

      <!-- Right: Assets -->
      <div class="assets-area">
        <div class="assets-toolbar">
          <div class="toolbar-left">
            <el-checkbox
              :model-value="isAllSelected"
              @change="toggleSelectAll"
            >全选</el-checkbox>
            <span class="assets-count">
              {{ categories.find(c => c.id === activeCategory)?.name || '全部素材' }}
              ({{ filteredAssets.length }})
            </span>
          </div>
          <el-button size="small" circle :icon="Refresh as any" />
        </div>

        <!-- Asset grid -->
        <div v-if="filteredAssets.length > 0" class="assets-grid">
          <div
            v-for="asset in filteredAssets"
            :key="asset.id"
            class="asset-card"
            :class="{ selected: selectedIds.includes(asset.id) }"
          >
            <div class="asset-thumb">
              <el-icon :size="28" color="var(--color-text-placeholder)"><VideoCamera /></el-icon>
              <el-checkbox
                class="asset-check"
                :model-value="selectedIds.includes(asset.id)"
                @change="(v: boolean) => {
                  if (v) selectedIds.push(asset.id)
                  else selectedIds = selectedIds.filter(i => i !== asset.id)
                }"
              />
            </div>
            <div class="asset-info">
              <p class="asset-name">{{ asset.name }}</p>
              <p class="asset-meta">{{ asset.size }} · {{ asset.date }}</p>
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <div v-else class="assets-empty">
          <el-icon :size="48" color="var(--color-text-placeholder)"><VideoCamera /></el-icon>
          <p>暂无素材</p>
          <el-button type="primary" round @click="openUpload">
            上传第一个素材
          </el-button>
        </div>
      </div>
    </div>

    <!-- Upload Panel (overlay) -->
    <el-dialog
      v-model="showUploadPanel"
      title=""
      width="700px"
      :show-close="true"
      destroy-on-close
    >
      <div class="upload-dialog">
        <!-- Steps indicator -->
        <div class="upload-steps">
          <div class="upload-step active">
            <span class="step-dot">1</span>
            <div>
              <p class="step-name">选择视频或图片</p>
              <p class="step-hint">选择文件和分类</p>
            </div>
          </div>
          <div class="step-line" />
          <div class="upload-step">
            <span class="step-dot">2</span>
            <div>
              <p class="step-name">标记与处理</p>
              <p class="step-hint">标记信息并完成向量化</p>
            </div>
          </div>
        </div>

        <div class="upload-body">
          <h3 class="upload-title">上传视频文件</h3>
          <p class="upload-subtitle">选择文件并标记分类</p>

          <!-- Category selector -->
          <div class="upload-field">
            <p class="u-field-label">选择分类</p>
            <div class="cat-select-row">
              <el-select v-model="uploadCategory" style="width: 240px;" size="large">
                <el-option
                  v-for="cat in categories"
                  :key="cat.id"
                  :label="cat.name"
                  :value="cat.id"
                />
              </el-select>
              <el-button text type="primary" @click="showNewCat = true">
                <el-icon><Plus /></el-icon>
                新建分类
              </el-button>
            </div>
          </div>

          <!-- Upload area -->
          <el-upload
            drag
            action=""
            :auto-upload="false"
            accept=".mp4,.avi,.mov,.mkv,.jpg,.jpeg,.png"
            multiple
            class="upload-drop"
          >
            <div class="upload-inner">
              <el-icon :size="40" color="var(--color-text-placeholder)"><UploadFilled /></el-icon>
              <p class="upload-main-text">点击或拖拽文件到此区域</p>
              <p class="upload-hint-text">支持 mp4、avi、mov、mkv 等视频格式，以及 jpg/png 图片，支持批量上传</p>
            </div>
          </el-upload>
        </div>

        <div class="upload-footer">
          <el-button @click="showUploadPanel = false">返回</el-button>
          <el-button type="primary">下一步</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { Refresh } from '@element-plus/icons-vue'
export default { components: { Refresh } }
</script>

<style scoped>
.page-view {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* ===== Page Header ===== */
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.page-title {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--space-5);
  min-height: 0;
}

/* ===== Category Sidebar ===== */
.category-sidebar {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  height: fit-content;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.sidebar-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast);
  font-size: var(--text-sm);
}

.category-item:hover {
  background: var(--color-bg-hover);
}

.category-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: var(--font-medium);
}

.cat-name {
  flex: 1;
}

.cat-count {
  width: 22px;
  height: 22px;
  border-radius: var(--radius-full);
  background: var(--color-bg-hover);
  font-size: var(--text-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  font-weight: var(--font-medium);
}

.category-item.active .cat-count {
  background: var(--color-primary);
  color: white;
}

.new-cat-form {
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.new-cat-btns {
  display: flex;
  gap: var(--space-2);
  justify-content: flex-end;
}

/* ===== Assets Area ===== */
.assets-area {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.assets-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border-light);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.assets-count {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}

.assets-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--space-4);
  overflow-y: auto;
}

.asset-card {
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.asset-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.asset-card.selected {
  border-color: var(--color-primary);
}

.asset-thumb {
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--color-bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.asset-check {
  position: absolute;
  top: var(--space-2);
  left: var(--space-2);
}

.asset-info {
  padding: var(--space-2) var(--space-3) var(--space-3);
}

.asset-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-meta {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.assets-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  padding: var(--space-16) 0;
}

/* ===== Upload Dialog ===== */
.upload-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.upload-steps {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-4);
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.upload-step {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  flex-shrink: 0;
}

.upload-step.active .step-dot {
  background: var(--color-primary);
  color: white;
}

.step-name {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.step-hint {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.step-line {
  flex: 1;
  height: 1px;
  background: var(--color-border-light);
}

.upload-body {
  text-align: center;
}

.upload-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.upload-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-top: 2px;
  margin-bottom: var(--space-5);
}

.upload-field {
  text-align: left;
  margin-bottom: var(--space-5);
}

.u-field-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.cat-select-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.upload-drop :deep(.el-upload) {
  width: 100%;
}

.upload-drop :deep(.el-upload-dragger) {
  width: 100%;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-page);
  padding: var(--space-8) var(--space-4);
  transition: border-color var(--duration-fast);
}

.upload-drop :deep(.el-upload-dragger:hover) {
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

.upload-hint-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.upload-footer {
  display: flex;
  justify-content: center;
  gap: var(--space-3);
}

.upload-footer .el-button {
  min-width: 100px;
}
</style>
