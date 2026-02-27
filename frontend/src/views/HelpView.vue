<template>
  <div class="page-view">
    <div class="page-header">
      <h1 class="page-title">帮助中心</h1>
      <p class="page-desc">使用指南与常见问题</p>
    </div>
    <div class="help-sections">
      <div class="help-card">
        <h3>快速开始</h3>
        <ol>
          <li>在「设置」中配置 Deepseek API Key</li>
          <li>确保 CosyVoice / HeyGem 服务已启动</li>
          <li>回到首页，粘贴对标视频链接开始创作</li>
        </ol>
      </div>
      <div class="help-card">
        <h3>常见问题</h3>
        <div class="faq-item">
          <h4>Q: 文案提取失败？</h4>
          <p>请检查视频链接是否有效，以及 yt-dlp 是否已正确安装。</p>
        </div>
        <div class="faq-item">
          <h4>Q: 语音合成无反应？</h4>
          <p>请确认 CosyVoice 服务（默认端口 5000）已启动，可在「设置」页面查看服务状态。</p>
        </div>
        <div class="faq-item">
          <h4>Q: 如何添加音色？</h4>
          <p>将 .pt 音色文件放入 resources/voices/ 目录，重启服务即可。</p>
        </div>
      </div>
      <div class="help-card">
        <h3>技术支持</h3>
        <p>API 文档: <a href="http://localhost:8000/docs" target="_blank">http://localhost:8000/docs</a></p>
        <p>项目版本: v0.1.0</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-view { flex: 1; padding: var(--space-8); overflow-y: auto; max-width: 720px; }
.page-header { margin-bottom: var(--space-8); }
.page-title { font-size: var(--text-2xl); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-2); }
.page-desc { font-size: var(--text-base); color: var(--color-text-secondary); }
.help-sections { display: flex; flex-direction: column; gap: var(--space-5); }
.help-card { padding: var(--space-6); background: var(--color-bg-card); border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg); }
.help-card h3 { font-size: var(--text-md); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-4); }
.help-card ol { padding-left: var(--space-5); display: flex; flex-direction: column; gap: var(--space-2);
  font-size: var(--text-sm); color: var(--color-text-secondary); line-height: var(--leading-relaxed); }
.faq-item { margin-bottom: var(--space-4); }
.faq-item h4 { font-size: var(--text-sm); font-weight: var(--font-semibold); color: var(--color-text-primary); margin-bottom: var(--space-1); }
.faq-item p { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: var(--leading-relaxed); }
.help-card p { font-size: var(--text-sm); color: var(--color-text-secondary); margin-top: var(--space-2); }
.help-card a { color: var(--color-primary); }
</style>
