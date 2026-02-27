<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import PlatformLogo from '../components/icons/PlatformLogo.vue'

interface PlatformAccount {
  id: string
  platform: 'douyin' | 'xiaohongshu' | 'shipinhao' | 'kuaishou' | 'bilibili'
  nickname: string
  avatar: string
  status: 'connected' | 'expired' | 'disconnected'
  lastLogin: string
  followers: number
}

const accounts = ref<PlatformAccount[]>([])
const showAddDialog = ref(false)

const platforms = [
  { key: 'douyin', name: '抖音' },
  { key: 'xiaohongshu', name: '小红书' },
  { key: 'shipinhao', name: '视频号' },
  { key: 'kuaishou', name: '快手' },
  { key: 'bilibili', name: 'B站' },
]

function getStatusLabel(s: string) {
  const map: Record<string, string> = { connected: '已登录', expired: '已过期', disconnected: '未连接' }
  return map[s] || s
}

function getStatusType(s: string) {
  const map: Record<string, string> = { connected: 'success', expired: 'warning', disconnected: 'info' }
  return map[s] || 'info'
}

function handleAddAccount(platformKey: string) {
  showAddDialog.value = false
  ElMessage.info(`${platforms.find(p => p.key === platformKey)?.name} 账号绑定功能即将上线`)
}

function handleRefreshLogin(account: PlatformAccount) {
  ElMessage.info(`正在刷新 ${account.nickname} 的登录状态...`)
}

function handleRemoveAccount(account: PlatformAccount) {
  accounts.value = accounts.value.filter(a => a.id !== account.id)
  ElMessage.success('已移除')
}
</script>

<template>
  <div class="page-view">
    <!-- Page Header -->
    <div class="page-header-card">
      <div class="header-text">
        <h1 class="page-title">账号管理</h1>
        <p class="page-desc">管理各平台发布账号的登录状态和信息。提示：已登录成功的账号才会在发布时可以选择</p>
      </div>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加账号
      </el-button>
    </div>

    <!-- Connected Accounts -->
    <div v-if="accounts.length > 0" class="accounts-section">
      <div class="accounts-grid">
        <div
          v-for="account in accounts"
          :key="account.id"
          class="account-card"
        >
          <div class="ac-header">
            <PlatformLogo :platform="account.platform" :size="40" />
            <div class="ac-info">
              <h3 class="ac-nickname">{{ account.nickname }}</h3>
              <p class="ac-platform-name">{{ platforms.find(p => p.key === account.platform)?.name }}</p>
            </div>
            <el-tag size="small" :type="getStatusType(account.status)" effect="light" round>
              {{ getStatusLabel(account.status) }}
            </el-tag>
          </div>

          <div class="ac-meta">
            <div class="meta-item">
              <span class="meta-label">粉丝</span>
              <span class="meta-value">{{ account.followers.toLocaleString() }}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">最近登录</span>
              <span class="meta-value">{{ account.lastLogin }}</span>
            </div>
          </div>

          <div class="ac-actions">
            <el-button size="small" @click="handleRefreshLogin(account)">
              <el-icon><Refresh /></el-icon>
              刷新状态
            </el-button>
            <el-button size="small" type="danger" text @click="handleRemoveAccount(account)">
              移除
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-card">
      <div class="empty-content">
        <div class="empty-icon-grid">
          <PlatformLogo v-for="p in platforms" :key="p.key" :platform="p.key" :size="36" />
        </div>
        <h3>暂无账号</h3>
        <p>点击「添加账号」开始管理您的发布账号</p>
        <el-button type="primary" round @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加账号
        </el-button>
      </div>
    </div>

    <!-- Add Account Dialog -->
    <el-dialog v-model="showAddDialog" title="" width="520px" destroy-on-close>
      <div class="add-dialog">
        <h2 class="dialog-title">选择平台</h2>
        <p class="dialog-desc">选择要绑定的社媒平台，将通过浏览器扫码登录</p>

        <div class="platform-list">
          <div
            v-for="p in platforms"
            :key="p.key"
            class="platform-option"
            @click="handleAddAccount(p.key)"
          >
            <PlatformLogo :platform="p.key" :size="40" />
            <div class="po-info">
              <h4>{{ p.name }}</h4>
              <p>通过扫码登录绑定账号</p>
            </div>
            <el-icon color="var(--color-text-tertiary)"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </el-dialog>
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

/* ===== Header ===== */
.page-header-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.page-title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: 2px;
}

.page-desc {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  line-height: var(--leading-relaxed);
}

/* ===== Account Cards ===== */
.accounts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--space-4);
}

.account-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  transition: all var(--duration-fast);
}

.account-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.ac-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.ac-platform-badge {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.ac-info {
  flex: 1;
}

.ac-nickname {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.ac-platform-name {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 1px;
}

.ac-meta {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-3);
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.meta-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.ac-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* ===== Empty State ===== */
.empty-card {
  flex: 1;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-10);
}

.empty-icon-grid {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.empty-platform-dot {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.empty-content h3 {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.empty-content p {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

/* ===== Add Dialog ===== */
.add-dialog {
  padding: var(--space-2);
}

.dialog-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  text-align: center;
}

.dialog-desc {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  text-align: center;
  margin-bottom: var(--space-5);
}

.platform-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.platform-option {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--duration-fast);
}

.platform-option:hover {
  background: var(--color-bg-hover);
}

.po-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.po-info {
  flex: 1;
}

.po-info h4 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.po-info p {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 1px;
}
</style>
