<script setup lang="ts">
import { ref, computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  stepNumber: number
  title: string
  completed?: boolean
  loading?: boolean
  active?: boolean
}>(), {
  completed: false,
  loading: false,
  active: false,
})

const emit = defineEmits<{
  toggle: []
}>()

const isExpanded = ref(props.active)

// Auto-expand when step becomes active
watch(() => props.active, (val) => {
  if (val) isExpanded.value = true
})

function toggle() {
  isExpanded.value = !isExpanded.value
  emit('toggle')
}

const statusClass = computed(() => {
  if (props.loading) return 'loading'
  if (props.completed) return 'completed'
  return 'pending'
})
</script>

<template>
  <div class="step-card" :class="{ expanded: isExpanded, active: props.active, 'is-loading': props.loading }">
    <div class="step-header" @click="toggle">
      <div class="step-number" :class="statusClass">
        <el-icon v-if="props.completed" :size="14"><Check /></el-icon>
        <el-icon v-else-if="props.loading" :size="14" class="spin"><Loading /></el-icon>
        <span v-else>{{ props.stepNumber }}</span>
      </div>
      <h3 class="step-title">{{ props.title }}</h3>
      <div class="step-badge" v-if="props.completed">
        <span>已完成</span>
      </div>
      <el-icon class="step-arrow" :class="{ rotated: isExpanded }" :size="16">
        <ArrowDown />
      </el-icon>
    </div>
    <transition name="collapse">
      <div v-show="isExpanded" class="step-body">
        <slot />
      </div>
    </transition>
  </div>
</template>

<style scoped>
.step-card {
  position: relative;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  transition: all var(--duration-normal) var(--ease-out);
  overflow: hidden;
}

.step-card.is-loading {
  border-color: transparent !important;
}

.step-card.is-loading::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 250%;
  height: 250%;
  background: conic-gradient(
    from 0deg,
    transparent 0%,
    transparent 50%,
    var(--color-primary-lighter) 80%,
    var(--color-primary) 100%
  );
  transform: translate(-50%, -50%);
  animation: border-neon-spin 2.5s linear infinite;
  z-index: 0;
  pointer-events: none;
}

.step-card.is-loading::after {
  content: '';
  position: absolute;
  inset: 1.5px;
  background: var(--color-bg-card);
  border-radius: calc(var(--radius-lg) - 1.5px);
  z-index: 0;
  pointer-events: none;
}

@keyframes border-neon-spin {
  0% { transform: translate(-50%, -50%) rotate(0deg); }
  100% { transform: translate(-50%, -50%) rotate(360deg); }
}

.step-card:hover {
  border-color: var(--color-border);
  box-shadow: var(--shadow-xs);
}

.step-card.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px var(--color-primary-bg);
}

.step-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  cursor: pointer;
  transition: background-color var(--duration-fast);
  z-index: 1;
}

.step-header:hover {
  background-color: var(--color-bg-hover);
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  flex-shrink: 0;
  transition: all var(--duration-normal) var(--ease-out);
}

.step-number.pending {
  background: var(--color-bg-hover);
  color: var(--color-text-tertiary);
}

.step-number.completed {
  background: var(--color-success);
  color: white;
}

.step-number.loading {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.step-title {
  flex: 1;
  font-size: var(--text-base);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.step-badge {
  padding: 2px var(--space-2);
  background: rgba(76, 175, 80, 0.1);
  color: var(--color-success);
  font-size: var(--text-xs);
  border-radius: var(--radius-full);
  font-weight: var(--font-medium);
}

.step-arrow {
  color: var(--color-text-tertiary);
  transition: transform var(--duration-normal) var(--ease-out);
  flex-shrink: 0;
}

.step-arrow.rotated {
  transform: rotate(180deg);
}

.step-body {
  position: relative;
  padding: 0 var(--space-5) var(--space-5);
  z-index: 1;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
