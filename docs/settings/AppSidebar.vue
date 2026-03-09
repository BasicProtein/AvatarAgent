<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConfigStore } from '../../stores/config'

const route = useRoute()
const router = useRouter()
const configStore = useConfigStore()

const menuItems = [
  { path: '/', label: '首页', icon: 'HomeFilled' },
  { path: '/voices', label: '声音管理', icon: 'Microphone' },
  { path: '/avatars', label: '形象管理', icon: 'User' },
  { path: '/assets', label: '素材管理', icon: 'FolderOpened' },
  { path: '/tasks', label: '任务中心', icon: 'List' },
  { path: '/accounts', label: '账号管理', icon: 'Connection' },
]

const bottomMenuItems = [
  { path: '/profile', label: '个人中心', icon: 'Avatar' },
  { path: '/settings', label: '设置', icon: 'Setting' },
  { path: '/help', label: '帮助', icon: 'QuestionFilled' },
]

const activePath = computed(() => route.path)

function navigateTo(path: string) {
  router.push(path)
}

const serviceOnlineCount = computed(() => {
  const s = configStore.services
  return [s.cosyvoice, s.heygem, s.tuilionnx].filter((v) => v === 'online').length
})
</script>

<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo" @click="navigateTo('/')">
      <div class="logo-icon">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="8" fill="var(--color-primary)" />
          <path d="M8 10L14 6L20 10V18L14 22L8 18V10Z" stroke="white" stroke-width="1.5" fill="none" />
          <circle cx="14" cy="14" r="3" fill="white" />
        </svg>
      </div>
      <span class="logo-text">AvatarAgent</span>
    </div>

    <!-- Main menu -->
    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li
          v-for="item in menuItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: activePath === item.path }"
          @click="navigateTo(item.path)"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </li>
      </ul>
    </nav>

    <!-- Spacer -->
    <div class="sidebar-spacer" />

    <!-- Service status indicator -->
    <div class="service-status">
      <div class="status-dot" :class="serviceOnlineCount > 0 ? 'online' : 'offline'" />
      <span class="status-text">{{ serviceOnlineCount }}/3 服务在线</span>
    </div>

    <!-- Bottom menu -->
    <nav class="sidebar-nav bottom-nav">
      <ul class="nav-list">
        <li
          v-for="item in bottomMenuItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: activePath === item.path }"
          @click="navigateTo(item.path)"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </li>
      </ul>
    </nav>

    <!-- Theme toggle -->
    <div class="theme-toggle" @click="configStore.toggleTheme()">
      <el-icon :size="16">
        <Sunny v-if="configStore.theme === 'dark'" />
        <Moon v-else />
      </el-icon>
      <span class="nav-label">{{ configStore.theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: var(--sidebar-width);
  height: 100vh;
  background-color: var(--color-bg-sidebar);
  border-right: 1px solid var(--color-border-light);
  display: flex;
  flex-direction: column;
  padding: var(--space-3) var(--space-2);
  flex-shrink: 0;
  transition: background-color var(--duration-normal) var(--ease-out);
  user-select: none;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  margin-bottom: var(--space-4);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: background-color var(--duration-fast);
}

.sidebar-logo:hover {
  background-color: var(--color-bg-hover);
}

.logo-text {
  font-size: var(--text-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.sidebar-nav {
  flex-shrink: 0;
}

.nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--duration-fast) var(--ease-out);
}

.nav-item:hover {
  background-color: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.nav-item.active {
  background-color: var(--color-primary-bg);
  color: var(--color-primary);
}

.nav-item.active .el-icon {
  color: var(--color-primary);
}

.sidebar-spacer {
  flex: 1;
}

.service-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.online {
  background-color: var(--color-success);
  box-shadow: 0 0 6px rgba(76, 175, 80, 0.4);
}

.status-dot.offline {
  background-color: var(--color-error);
  box-shadow: 0 0 6px rgba(229, 57, 53, 0.4);
}

.bottom-nav {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

.theme-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  margin-top: var(--space-1);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  transition: all var(--duration-fast) var(--ease-out);
}

.theme-toggle:hover {
  background-color: var(--color-bg-hover);
  color: var(--color-text-secondary);
}
</style>
