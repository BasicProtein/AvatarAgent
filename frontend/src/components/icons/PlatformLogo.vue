<script setup lang="ts">
defineProps<{
  platform: string
  size?: number
}>()
</script>

<template>
  <!-- 抖音 Douyin -->
  <div v-if="platform === 'douyin'" class="logo-wrap" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="10" fill="#000"/>
      <path d="M33.5 20.2c-1.8 1.2-4 1.9-6.3 1.9v-1c.3 0 .5 0 .8-.1v-4.4a11.6 11.6 0 0 1-3.2.5v5.3c0 5.5-4.4 10-9.8 10.4a9.7 9.7 0 0 1-2.4-.1 10 10 0 0 0 6.2 2.2c5.6 0 10.1-4.6 10.1-10.3v-5.6a13.5 13.5 0 0 0 6.3 1.6v-4.5c-1 0-1.8-.2-2.6-.5z" fill="#25F4EE"/>
      <path d="M28 21.1v-4.4c1.5.4 3 .5 4.5.1v3.2a11.5 11.5 0 0 1-5.6-1.3v5.6c0 5.7-4.5 10.3-10.1 10.3-2 0-3.9-.6-5.5-1.6C13.4 35 16.2 36 19.2 36c5.6 0 10.1-4.6 10.1-10.3v-5.6c1.6 1 3.5 1.6 5.6 1.3v-3.2c-1.5-.3-2.8-1-3.8-2l-3.1 4.9z" fill="#FE2C55"/>
      <path d="M19.8 26.3c-2 .3-3.6 2-3.6 4.1 0 1.7 1 3.1 2.5 3.8-.6-.7-.9-1.6-.9-2.5 0-2.1 1.6-3.8 3.6-4.1v-4.3h-1.6v3z" fill="#FE2C55"/>
    </svg>
  </div>

  <!-- 小红书 Xiaohongshu / RED -->
  <div v-else-if="platform === 'xiaohongshu'" class="logo-wrap" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="10" fill="#FF2442"/>
      <g fill="#fff">
        <path d="M15 12h6l1.5 6H15V12z"/>
        <path d="M24 12h6v6h-7.5L24 12z"/>
        <path d="M14 20h20v3H14z"/>
        <path d="M15 23h5v13h-5z"/>
        <path d="M28 23h5v13h-5z"/>
        <path d="M20 30h8v3h-8z"/>
        <text x="24" y="40" text-anchor="middle" font-size="7" font-weight="bold" fill="rgba(255,255,255,0.3)">RED</text>
      </g>
    </svg>
  </div>

  <!-- 视频号 WeChat Channels -->
  <div v-else-if="platform === 'shipinhao'" class="logo-wrap" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="10" fill="#FA9D3B"/>
      <g fill="#fff">
        <!-- Camera lens -->
        <circle cx="24" cy="22" r="9" fill="none" stroke="#fff" stroke-width="2.5"/>
        <circle cx="24" cy="22" r="4"/>
        <!-- Star sparkle -->
        <path d="M35 10l1.2 2.5 2.8.4-2 2 .5 2.7L35 16.3l-2.5 1.3.5-2.7-2-2 2.8-.4L35 10z"/>
        <!-- Bottom bar -->
        <rect x="13" y="34" width="22" height="3" rx="1.5"/>
      </g>
    </svg>
  </div>

  <!-- 快手 Kuaishou -->
  <div v-else-if="platform === 'kuaishou'" class="logo-wrap" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="10" fill="#FF4906"/>
      <g fill="#fff">
        <!-- Film strip / play icon -->
        <rect x="11" y="12" width="26" height="24" rx="4" fill="none" stroke="#fff" stroke-width="2.5"/>
        <polygon points="20,17 20,31 33,24"/>
      </g>
    </svg>
  </div>

  <!-- B站 Bilibili -->
  <div v-else-if="platform === 'bilibili'" class="logo-wrap" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="48" height="48" rx="10" fill="#FB7299"/>
      <g fill="#fff">
        <!-- TV body -->
        <rect x="9" y="16" width="30" height="20" rx="4"/>
        <!-- Antenna left -->
        <path d="M16 16l-4-6" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Antenna right -->
        <path d="M32 16l4-6" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>
        <!-- Eyes -->
        <ellipse cx="19" cy="26" rx="2.5" ry="3" fill="#FB7299"/>
        <ellipse cx="29" cy="26" rx="2.5" ry="3" fill="#FB7299"/>
      </g>
    </svg>
  </div>

  <!-- Fallback -->
  <div v-else class="logo-wrap fallback" :style="{ width: (size || 40) + 'px', height: (size || 40) + 'px' }">
    <el-icon :size="(size || 40) * 0.5"><Monitor /></el-icon>
  </div>
</template>

<style scoped>
.logo-wrap {
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
}

.logo-wrap svg {
  width: 100%;
  height: 100%;
  display: block;
}

.fallback {
  background: var(--color-bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}
</style>
