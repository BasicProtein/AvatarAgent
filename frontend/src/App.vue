<script setup lang="ts">
import { onMounted } from 'vue'
import { useConfigStore } from './stores/config'
import AppSidebar from './components/layout/AppSidebar.vue'

const configStore = useConfigStore()

onMounted(() => {
  configStore.initTheme()
  configStore.fetchServices()
  configStore.fetchApiKeys()
})
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background-color: var(--color-bg-page);
}

.app-main {
  flex: 1;
  overflow: hidden;
  display: flex;
}
</style>
