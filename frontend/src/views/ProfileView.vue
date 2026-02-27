<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
      <p class="page-desc">个人信息与使用统计</p>
    </div>
    <div class="profile-card">
      <div class="profile-avatar">
        <el-icon :size="36"><User /></el-icon>
      </div>
      <div class="profile-info">
        <h3>AvatarAgent 用户</h3>
        <p>本地版本 v0.1.0</p>
      </div>
    </div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">0</div>
        <div class="stat-label">已创建视频</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">0</div>
        <div class="stat-label">已发布视频</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">0</div>
        <div class="stat-label">使用天数</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-view { flex: 1; padding: var(--space-8); overflow-y: auto; }
.page-header { margin-bottom: var(--space-8); }
.page-title { font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.page-desc { font-size: var(--text-base); color: var(--color-text-secondary); }
.profile-card { display: flex; align-items: center; gap: var(--space-5); padding: var(--space-6); background: var(--color-bg-card);
  border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); margin-bottom: var(--space-6); }
.profile-avatar { width: 64px; height: 64px; border-radius: 50%; background: var(--color-primary-bg); color: var(--color-primary);
  display: flex; align-items: center; justify-content: center; }
.profile-info h3 { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--color-text-primary); }
.profile-info p { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: 2px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-4); }
.stat-card { text-align: center; padding: var(--space-6); background: var(--color-bg-card);
  border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); }
.stat-value { font-size: var(--text-3xl); font-weight: var(--font-semibold); color: var(--color-primary); }
.stat-label { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-top: var(--space-1); }
</style>
