<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfigStore } from '../stores/config'
import { ElMessage } from 'element-plus'

const configStore = useConfigStore()
const newKey = ref('')

onMounted(() => {
  configStore.fetchApiKeys()
  configStore.fetchServices()
})

async function addKey() {
  if (!newKey.value.trim()) return
  try {
    const { configApi } = await import('../api/config')
    await configApi.addApiKey(newKey.value.trim())
    await configStore.fetchApiKeys()
    newKey.value = ''
    ElMessage.success('API Key 添加成功')
  } catch {
    ElMessage.error('添加失败')
  }
}

async function removeKey(key: string) {
  try {
    const { configApi } = await import('../api/config')
    await configApi.deleteApiKey(key)
    await configStore.fetchApiKeys()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}
</script>

<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <p class="page-desc">应用配置与偏好设置</p>
    </div>

    <!-- Theme -->
    <div class="settings-section">
      <h2 class="section-title">外观</h2>
      <div class="setting-item">
        <div class="setting-info">
          <h3>主题模式</h3>
          <p>切换浅色/深色主题</p>
        </div>
        <el-switch
          :model-value="configStore.theme === 'dark'"
          @change="configStore.toggleTheme()"
          active-text="深色"
          inactive-text="浅色"
        />
      </div>
    </div>

    <!-- API Keys -->
    <div class="settings-section">
      <h2 class="section-title">API Key 管理</h2>
      <div class="key-input-row">
        <el-input v-model="newKey" placeholder="输入 Deepseek API Key..." size="large" />
        <el-button type="primary" size="large" @click="addKey">添加</el-button>
      </div>
      <div class="key-list">
        <div v-for="key in configStore.apiKeys" :key="key" class="key-item">
          <span class="key-text">{{ key.slice(0, 10) }}...{{ key.slice(-6) }}</span>
          <el-button type="danger" size="small" text @click="removeKey(key)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <p v-if="configStore.apiKeys.length === 0" class="hint">暂未配置 API Key</p>
      </div>
    </div>

    <!-- Services -->
    <div class="settings-section">
      <h2 class="section-title">服务状态</h2>
      <div class="service-list">
        <div class="service-item">
          <span>CosyVoice (语音合成)</span>
          <el-tag :type="configStore.services.cosyvoice === 'online' ? 'success' : 'danger'" size="small">
            {{ configStore.services.cosyvoice === 'online' ? '在线' : '离线' }}
          </el-tag>
        </div>
        <div class="service-item">
          <span>HeyGem (数字人)</span>
          <el-tag :type="configStore.services.heygem === 'online' ? 'success' : 'danger'" size="small">
            {{ configStore.services.heygem === 'online' ? '在线' : '离线' }}
          </el-tag>
        </div>
        <div class="service-item">
          <span>TuiliONNX (数字人)</span>
          <el-tag :type="configStore.services.tuilionnx === 'online' ? 'success' : 'danger'" size="small">
            {{ configStore.services.tuilionnx === 'online' ? '在线' : '离线' }}
          </el-tag>
        </div>
      </div>
      <el-button size="small" @click="configStore.fetchServices()" style="margin-top: var(--space-3);">
        <el-icon><Refresh /></el-icon> 刷新状态
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.page-view { flex: 1; padding: var(--space-8); overflow-y: auto; max-width: 720px; }
.page-header { margin-bottom: var(--space-8); }
.page-title { font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.page-desc { font-size: var(--text-base); color: var(--color-text-secondary); }
.settings-section { margin-bottom: var(--space-8); }
.section-title { font-size: var(--text-md); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-4);
  padding-bottom: var(--space-2); border-bottom: 1px solid var(--color-border-light); }
.setting-item { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4);
  background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.setting-info h3 { font-size: var(--text-base); font-weight: var(--font-medium); color: var(--color-text-primary); }
.setting-info p { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: 2px; }
.key-input-row { display: flex; gap: var(--space-3); margin-bottom: var(--space-4); }
.key-list { display: flex; flex-direction: column; gap: var(--space-2); }
.key-item { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4);
  background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-md); }
.key-text { font-family: var(--font-mono); font-size: var(--text-sm); color: var(--color-text-secondary); }
.hint { font-size: var(--text-sm); color: var(--color-text-tertiary); }
.service-list { display: flex; flex-direction: column; gap: var(--space-2); }
.service-item { display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-4);
  background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-md);
  font-size: var(--text-sm); color: var(--color-text-primary); }
</style>
