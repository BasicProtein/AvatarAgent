<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// Task data
interface TaskItem {
  id: string
  title: string
  mode: 'auto' | 'manual'
  status: 'running' | 'completed' | 'failed' | 'pending'
  progress: number
  currentStep: string
  createdAt: string
  enabled: boolean
}

const tasks = ref<TaskItem[]>([])
const loading = ref(false)

// Filters
const filterStatus = ref('')
const filterMode = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '进行中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '失败', value: 'failed' },
  { label: '待处理', value: 'pending' },
]

const modeOptions = [
  { label: '全部模式', value: '' },
  { label: '自动', value: 'auto' },
  { label: '手动', value: 'manual' },
]

// Stats
const stats = computed(() => ({
  total: tasks.value.length,
  running: tasks.value.filter(t => t.status === 'running').length,
  completed: tasks.value.filter(t => t.status === 'completed').length,
  failed: tasks.value.filter(t => t.status === 'failed').length,
}))

const filteredTasks = computed(() => {
  let list = tasks.value
  if (filterStatus.value) list = list.filter(t => t.status === filterStatus.value)
  if (filterMode.value) list = list.filter(t => t.mode === filterMode.value)
  return list
})

const pagedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredTasks.value.slice(start, start + pageSize.value)
})

function clearFilters() {
  filterStatus.value = ''
  filterMode.value = ''
}

function getStatusLabel(s: string) {
  const map: Record<string, string> = { running: '处理中', completed: '已完成', failed: '失败', pending: '待处理' }
  return map[s] || s
}

function getStatusType(s: string) {
  const map: Record<string, string> = { running: 'primary', completed: 'success', failed: 'danger', pending: 'info' }
  return map[s] || 'info'
}

function getStepLabel(step: string) {
  const map: Record<string, string> = {
    extract: '提取', rewrite: '仿写', synthesize: '语音', avatar: '数字人', postprod: '后期', publish: '发布'
  }
  return map[step] || step
}

async function handleDelete(task: TaskItem) {
  try {
    await ElMessageBox.confirm(`确定删除任务「${task.title}」？`, '删除确认', { type: 'warning' })
    tasks.value = tasks.value.filter(t => t.id !== task.id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

function handleRefresh() {
  ElMessage.info('刷新中...')
  // TODO: fetch tasks from API
}

function handleNewTask() {
  ElMessage.info('新建任务功能即将上线')
}
</script>

<template>
  <div class="page-view">
    <!-- Top Banner -->
    <div class="banner-card">
      <div class="banner-left">
        <div class="banner-icon">
          <el-icon :size="24"><DataLine /></el-icon>
        </div>
        <div>
          <h1 class="banner-title">任务中心</h1>
          <p class="banner-desc">这里存储着你的任务。如果很久很久没用，或你曾经移动过任务里的一些视频音频文件，可能导致再次制作时失败，清楚注意即可。</p>
        </div>
      </div>
      <div class="banner-actions">
        <el-button @click="handleRefresh">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="handleNewTask">
          <el-icon><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon total">
          <el-icon :size="22"><DataBoard /></el-icon>
        </div>
        <div class="stat-body">
          <p class="stat-label">总任务</p>
          <p class="stat-value">{{ stats.total }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon running">
          <el-icon :size="22"><Loading /></el-icon>
        </div>
        <div class="stat-body">
          <p class="stat-label">进行中</p>
          <p class="stat-value">{{ stats.running }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon completed">
          <el-icon :size="22"><CircleCheck /></el-icon>
        </div>
        <div class="stat-body">
          <p class="stat-label">已完成</p>
          <p class="stat-value">{{ stats.completed }}</p>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon failed">
          <el-icon :size="22"><CircleClose /></el-icon>
        </div>
        <div class="stat-body">
          <p class="stat-label">失败</p>
          <p class="stat-value">{{ stats.failed }}</p>
        </div>
      </div>
    </div>

    <!-- Filter Bar -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-icon :size="16" color="var(--color-text-tertiary)"><Search /></el-icon>
        <span class="filter-label">筛选条件</span>
        <el-select v-model="filterStatus" placeholder="任务状态" size="default" style="width: 140px;" clearable>
          <el-option v-for="opt in statusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-select v-model="filterMode" placeholder="执行模式" size="default" style="width: 140px;" clearable>
          <el-option v-for="opt in modeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" size="default">筛选</el-button>
        <el-button size="default" @click="clearFilters">清空</el-button>
      </div>
    </div>

    <!-- Task Table -->
    <div class="table-card">
      <el-table :data="pagedTasks" stripe style="width: 100%;" v-loading="loading" empty-text="暂无任务记录">
        <el-table-column prop="title" label="任务标题" min-width="200">
          <template #default="{ row }">
            <div class="task-title-cell">
              <span class="task-name">{{ row.title }}</span>
              <el-tag size="small" :type="row.mode === 'auto' ? 'success' : 'warning'" effect="plain" round>
                {{ row.mode === 'auto' ? '自动' : '手动' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="getStatusType(row.status)" effect="light">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="140">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :stroke-width="6"
              :status="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'exception' : undefined"
            />
          </template>
        </el-table-column>
        <el-table-column label="当前步骤" width="100">
          <template #default="{ row }">
            <span class="step-tag">{{ getStepLabel(row.currentStep) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="createdAt" label="创建时间" width="180" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-cell">
              <el-switch v-model="row.enabled" size="small" />
              <el-button type="primary" text size="small">详情</el-button>
              <el-button type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination-bar">
        <span class="total-text">共 {{ filteredTasks.length }} 条记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="filteredTasks.length"
          :page-sizes="[10, 20, 50]"
          layout="prev, pager, next, sizes"
          small
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-view {
  flex: 1;
  padding: var(--space-6);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* ===== Banner ===== */
.banner-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.banner-left {
  display: flex;
  gap: var(--space-3);
  flex: 1;
}

.banner-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.banner-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.banner-desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  line-height: var(--leading-relaxed);
}

.banner-actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}

/* ===== Stats Row ===== */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4) var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  transition: box-shadow var(--duration-fast);
}

.stat-card:hover {
  box-shadow: var(--shadow-xs);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.total {
  background: rgba(var(--color-primary-rgb, 191, 100, 68), 0.1);
  color: var(--color-primary);
}

.stat-icon.running {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}

.stat-icon.completed {
  background: rgba(76, 175, 80, 0.1);
  color: var(--color-success);
}

.stat-icon.failed {
  background: rgba(244, 67, 54, 0.1);
  color: var(--color-error);
}

.stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-bottom: 2px;
}

.stat-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

/* ===== Filter Bar ===== */
.filter-bar {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
}

.filter-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.filter-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

/* ===== Table Card ===== */
.table-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  flex: 1;
  display: flex;
  flex-direction: column;
}

.task-title-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.task-name {
  font-weight: var(--font-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.step-tag {
  font-size: var(--text-xs);
  padding: 2px var(--space-2);
  background: var(--color-bg-hover);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.action-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* ===== Pagination ===== */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border-light);
  margin-top: var(--space-4);
}

.total-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
