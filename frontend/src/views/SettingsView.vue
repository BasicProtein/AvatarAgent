<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useConfigStore } from '../stores/config'
import { configApi, type CloudGpuConfig, type LocalAsrStatus } from '../api/config'
import { ElMessage } from 'element-plus'

const configStore = useConfigStore()
const newKey = ref('')

// ── 云端 GPU 配置 ────────────────────────────────────────────────────────────
const cloudGpu = ref<CloudGpuConfig>({ enabled: false, api_url: '', api_key: '' })
const cloudGpuTesting = ref(false)
const cloudGpuTestResult = ref<{ status: string; model?: string; message?: string } | null>(null)
const cloudGpuSaving = ref(false)

// ── 本地 ASR 状态 ────────────────────────────────────────────────────────────
const localAsr = ref<LocalAsrStatus | null>(null)
const localAsrLoading = ref(false)
const selectedModel = ref('turbo')
const modelSaving = ref(false)

const WHISPER_MODELS = [
  { value: 'turbo',  label: 'turbo  （推荐）', size: '~809MB', desc: '速度快且精度高' },
  { value: 'large',  label: 'large',  size: '~2.9GB', desc: '精度最高，速度慢' },
  { value: 'medium', label: 'medium', size: '~1.5GB', desc: '精度好，速度中' },
  { value: 'small',  label: 'small',  size: '~466MB', desc: '平衡选项' },
  { value: 'base',   label: 'base',   size: '~145MB', desc: '极快，精度一般' },
  { value: 'tiny',   label: 'tiny',   size: '~75MB',  desc: '极小模型' },
]

const localAsrStatusLabel = computed(() => {
  if (!localAsr.value) return { text: '检测中...', cls: '' }
  if (!localAsr.value.whisper_installed) return { text: '未安装', cls: 'missing' }
  if (localAsr.value.device === 'cuda') return { text: `GPU 加速 (${localAsr.value.gpu_name})`, cls: 'gpu' }
  if (localAsr.value.device === 'mps')  return { text: `Apple GPU 加速`, cls: 'gpu' }
  return { text: 'CPU 模式', cls: 'cpu' }
})

onMounted(async () => {
  configStore.fetchApiKeys()
  configStore.fetchServices()
  // 加载云端 GPU 配置
  try {
    const res = await configApi.getCloudGpu()
    cloudGpu.value = res.data
  } catch { /* 忽略 */ }
  // 加载本地 ASR 状态
  await refreshLocalAsr()
})

async function refreshLocalAsr() {
  localAsrLoading.value = true
  try {
    const res = await configApi.getLocalAsr()
    localAsr.value = res.data
    selectedModel.value = res.data.model_size || 'turbo'
  } catch { /* 忽略 */ } finally {
    localAsrLoading.value = false
  }
}

async function saveWhisperModel() {
  modelSaving.value = true
  try {
    await configApi.setWhisperModel(selectedModel.value)
    ElMessage.success(`Whisper 模型已设为 ${selectedModel.value}`)
  } catch {
    ElMessage.error('保存失败')
  } finally {
    modelSaving.value = false
  }
}

async function addKey() {
  if (!newKey.value.trim()) return
  try {
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
    await configApi.deleteApiKey(key)
    await configStore.fetchApiKeys()
    ElMessage.success('已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

async function saveCloudGpu() {
  cloudGpuSaving.value = true
  try {
    await configApi.setCloudGpu(cloudGpu.value)
    ElMessage.success('云端 GPU 配置已保存')
    cloudGpuTestResult.value = null
  } catch {
    ElMessage.error('保存失败')
  } finally {
    cloudGpuSaving.value = false
  }
}

async function testCloudGpu() {
  await saveCloudGpu()
  cloudGpuTesting.value = true
  cloudGpuTestResult.value = null
  try {
    const res = await configApi.testCloudGpu()
    cloudGpuTestResult.value = res.data
    if (res.data.status === 'online') {
      ElMessage.success(`连接成功！模型: ${res.data.model}`)
    } else {
      ElMessage.error(res.data.message || '连接失败')
    }
  } catch {
    cloudGpuTestResult.value = { status: 'error', message: '请求异常' }
    ElMessage.error('测试请求失败')
  } finally {
    cloudGpuTesting.value = false
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

    <!-- Local ASR (Whisper) -->
    <div class="settings-section">
      <h2 class="section-title">本地 ASR（Whisper）</h2>
      <p class="section-desc">
        语音识别核心模块，将音频转为文字。<br />
        安装后<strong>自动检测 GPU</strong>，有 NVIDIA 显卡时自动 CUDA 加速，无 GPU 时在 CPU 上运行。
      </p>

      <!-- 状态行 -->
      <div class="asr-status-row">
        <div class="asr-badge" :class="localAsrStatusLabel.cls">
          {{ localAsrStatusLabel.text }}
        </div>
        <el-button size="small" :loading="localAsrLoading" @click="refreshLocalAsr">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>

      <!-- 详细信息 -->
      <div v-if="localAsr" class="asr-detail-grid">
        <div class="asr-detail-item">
          <span class="detail-label">Whisper</span>
          <span :class="localAsr.whisper_installed ? 'ok' : 'fail'">
            {{ localAsr.whisper_installed ? '✅ 已安装' : '❌ 未安装' }}
          </span>
        </div>
        <div class="asr-detail-item">
          <span class="detail-label">PyTorch</span>
          <span :class="localAsr.torch_installed ? 'ok' : 'warn'">
            {{ localAsr.torch_installed ? '✅ 已安装' : '⚠️ 未安装（将使用 CPU）' }}
          </span>
        </div>
        <div class="asr-detail-item" v-if="localAsr.gpu_name">
          <span class="detail-label">GPU</span>
          <span class="ok">{{ localAsr.gpu_name }}</span>
        </div>
        <div class="asr-detail-item">
          <span class="detail-label">推理设备</span>
          <span :class="localAsr.device !== 'cpu' ? 'ok' : ''">
            {{ localAsr.device.toUpperCase() }}
          </span>
        </div>
      </div>

      <!-- 未安装引导 -->
      <div v-if="localAsr && !localAsr.whisper_installed" class="install-guide">
        <p class="guide-title">安装本地 Whisper</p>
        <code class="cmd">uv add openai-whisper</code>
        <p class="field-hint">首次运行时会自动下载 torch（CPU 版）和 Whisper 模型文件。</p>
      </div>

      <!-- 已安装但无 CUDA：GPU 升级引导 -->
      <div v-if="localAsr && localAsr.whisper_installed && !localAsr.cuda_available" class="install-guide warn">
        <p class="guide-title">可选：安装 CUDA GPU 加速版 PyTorch</p>
        <p class="field-hint">当前在 CPU 模式运行（速度较慢）。如有 NVIDIA 显卡，可升级为 GPU 加速：</p>
        <code class="cmd">pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121</code>
        <p class="field-hint">安装后刷新此页面即可看到 GPU 信息。CUDA 12.1 版本适合大多数 RTX 显卡。</p>
      </div>

      <!-- 模型大小选择 -->
      <div v-if="localAsr && localAsr.whisper_installed" class="model-select-row">
        <label class="field-label">Whisper 模型大小</label>
        <div class="model-options">
          <div
            v-for="m in WHISPER_MODELS"
            :key="m.value"
            class="model-option"
            :class="{ selected: selectedModel === m.value }"
            @click="selectedModel = m.value"
          >
            <span class="model-name">{{ m.label }}</span>
            <span class="model-size">{{ m.size }}</span>
            <span class="model-desc">{{ m.desc }}</span>
          </div>
        </div>
        <el-button type="primary" :loading="modelSaving" @click="saveWhisperModel" style="margin-top: var(--space-3);">
          保存模型配置
        </el-button>
      </div>
    </div>

    <!-- Cloud GPU (AutoDL) -->
    <div class="settings-section">
      <h2 class="section-title">云端 GPU（AutoDL）</h2>
      <p class="section-desc">
        本机 GPU 不足时，可接入 AutoDL 云端 GPU 运行 Whisper 语音识别。
        <br />
        需先在 AutoDL 实例上运行 <code>docs/autodl_whisper_server.py</code>，并开启 SSH 隧道（<code>docs/autodl_ssh_tunnel.bat</code>）。
      </p>

      <div class="cloud-gpu-panel">
        <!-- 开关 -->
        <div class="setting-item" style="margin-bottom: var(--space-3);">
          <div class="setting-info">
            <h3>启用云端 GPU</h3>
            <p>开启后 ASR 转录将发送到云端处理</p>
          </div>
          <el-switch v-model="cloudGpu.enabled" active-text="开启" inactive-text="关闭" />
        </div>

        <!-- 配置输入 -->
        <div v-if="cloudGpu.enabled" class="cloud-gpu-fields">
          <div class="field-row">
            <label class="field-label">API 地址</label>
            <el-input
              v-model="cloudGpu.api_url"
              placeholder="例如: http://127.0.0.1:6006"
              size="large"
              clearable
            >
              <template #prepend>URL</template>
            </el-input>
            <p class="field-hint">SSH 隧道模式填 <code>http://127.0.0.1:6006</code>；AutoDL 自定义服务则填公网地址</p>
          </div>

          <div class="field-row">
            <label class="field-label">访问密钥（可选）</label>
            <el-input
              v-model="cloudGpu.api_key"
              placeholder="留空表示无需认证"
              size="large"
              show-password
              clearable
            >
              <template #prepend>KEY</template>
            </el-input>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="cloud-gpu-actions">
          <el-button
            type="primary"
            :loading="cloudGpuSaving"
            @click="saveCloudGpu"
          >
            保存配置
          </el-button>
          <el-button
            v-if="cloudGpu.enabled"
            :loading="cloudGpuTesting"
            @click="testCloudGpu"
          >
            测试连接
          </el-button>
        </div>

        <!-- 测试结果 -->
        <div v-if="cloudGpuTestResult" class="test-result" :class="cloudGpuTestResult.status">
          <template v-if="cloudGpuTestResult.status === 'online'">
            ✅ 连接成功！Whisper 模型: <strong>{{ cloudGpuTestResult.model }}</strong>
          </template>
          <template v-else>
            ❌ {{ cloudGpuTestResult.message }}
          </template>
        </div>

        <!-- 接入指南 -->
        <div class="guide-block">
          <p class="guide-title">接入步骤</p>
          <ol class="guide-steps">
            <li>在 AutoDL 控制台租用 GPU 实例（推荐 RTX 3090/4090）</li>
            <li>将 <code>docs/autodl_whisper_server.py</code> 上传到实例，执行：
              <code class="cmd">pip install openai-whisper fastapi uvicorn python-multipart && python autodl_whisper_server.py</code>
            </li>
            <li>本地双击运行 <code>docs/autodl_ssh_tunnel.bat</code>（填写 AutoDL SSH 信息后）</li>
            <li>在上方填写 <code>http://127.0.0.1:6006</code> 并点击"测试连接"</li>
          </ol>
        </div>
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
.section-title { font-size: var(--text-md); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-2);
  padding-bottom: var(--space-2); border-bottom: 1px solid var(--color-border-light); }
.section-desc { font-size: var(--text-sm); color: var(--color-text-secondary); margin-bottom: var(--space-4); line-height: 1.6; }
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

/* Cloud GPU 面板 */
.cloud-gpu-panel { display: flex; flex-direction: column; gap: var(--space-4); }
.cloud-gpu-fields { display: flex; flex-direction: column; gap: var(--space-3); }
.field-row { display: flex; flex-direction: column; gap: var(--space-1); }
.field-label { font-size: var(--text-sm); font-weight: var(--font-medium); color: var(--color-text-secondary); }
.field-hint { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: var(--space-1); }
.cloud-gpu-actions { display: flex; gap: var(--space-3); }
.test-result {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  border: 1px solid;
}
.test-result.online { background: rgba(39, 174, 96, 0.08); border-color: rgba(39,174,96,0.3); color: #27AE60; }
.test-result.error { background: rgba(192, 57, 43, 0.08); border-color: rgba(192,57,43,0.3); color: #C0392B; }

/* 接入指南 */
.guide-block {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}
.guide-title { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.guide-steps { padding-left: var(--space-5); display: flex; flex-direction: column; gap: var(--space-2); }
.guide-steps li { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; }
code { font-family: var(--font-mono); background: rgba(0,0,0,0.06); padding: 1px 5px; border-radius: 3px; font-size: 0.9em; }
code.cmd {
  display: block;
  margin-top: var(--space-1);
  padding: var(--space-2) var(--space-3);
  background: rgba(0,0,0,0.08);
  border-radius: var(--radius-sm);
  word-break: break-all;
  white-space: pre-wrap;
}

/* ── 本地 ASR 面板 ─────────────────────────────────────────────────────── */
.asr-status-row { display: flex; align-items: center; gap: var(--space-3); margin-bottom: var(--space-3); }
.asr-badge {
  padding: var(--space-1) var(--space-4);
  border-radius: 999px;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  border: 1px solid;
}
.asr-badge.gpu     { background: rgba(39,174,96,0.1);  border-color: rgba(39,174,96,0.4);  color: #1e9e5c; }
.asr-badge.cpu     { background: rgba(243,156,18,0.1); border-color: rgba(243,156,18,0.4); color: #d68910; }
.asr-badge.missing { background: rgba(192,57,43,0.1);  border-color: rgba(192,57,43,0.4);  color: #a93226; }

.asr-detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.asr-detail-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
}
.detail-label { color: var(--color-text-tertiary); }
.ok   { color: #1e9e5c; font-weight: var(--font-medium); }
.fail { color: #c0392b; font-weight: var(--font-medium); }
.warn { color: #d68910; font-weight: var(--font-medium); }

.install-guide {
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
}
.install-guide.warn { border-color: rgba(243,156,18,0.3); background: rgba(243,156,18,0.05); }

.model-select-row { display: flex; flex-direction: column; gap: var(--space-2); }
.model-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}
.model-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space-3);
  background: var(--color-bg-card);
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.model-option:hover { border-color: var(--color-primary); }
.model-option.selected { border-color: var(--color-primary); background: rgba(var(--color-primary-rgb, 64,158,255), 0.06); }
.model-name { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--color-text-primary); font-family: var(--font-mono); }
.model-size { font-size: var(--text-xs); color: var(--color-text-secondary); }
.model-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); }
</style>
