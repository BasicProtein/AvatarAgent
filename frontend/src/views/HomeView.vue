<script setup lang="ts">
import { usePipelineStore } from '../stores/pipeline'
import StepCard from '../components/editor/StepCard.vue'
import ScriptExtractStep from '../components/editor/ScriptExtractStep.vue'
import ScriptRewriteStep from '../components/editor/ScriptRewriteStep.vue'
import ComplianceCheckStep from '../components/editor/ComplianceCheckStep.vue'
import AudioSynthesizeStep from '../components/editor/AudioSynthesizeStep.vue'
import AvatarGenerateStep from '../components/editor/AvatarGenerateStep.vue'
import VideoPostStep from '../components/editor/VideoPostStep.vue'
import PublishStep from '../components/editor/PublishStep.vue'
import PreviewPanel from '../components/preview/PreviewPanel.vue'

const pipeline = usePipelineStore()
</script>

<template>
  <div class="home-view">
    <!-- Editor panel -->
    <div class="editor-panel">
      <div class="editor-header">
        <h2 class="editor-title">视频创作工作流</h2>
        <span class="step-progress">{{ pipeline.completedCount }}/7 步完成</span>
      </div>

      <div class="editor-scroll">
        <div class="steps-list">
          <StepCard
            :step-number="1"
            title="文案提取"
            :completed="pipeline.steps.extract.completed"
            :loading="pipeline.steps.extract.loading"
            :active="pipeline.activeStep === 'extract'"
            @toggle="pipeline.setActiveStep('extract')"
          >
            <ScriptExtractStep />
          </StepCard>

          <StepCard
            :step-number="2"
            title="文案仿写"
            :completed="pipeline.steps.rewrite.completed"
            :loading="pipeline.steps.rewrite.loading"
            :active="pipeline.activeStep === 'rewrite'"
            @toggle="pipeline.setActiveStep('rewrite')"
          >
            <ScriptRewriteStep />
          </StepCard>

          <StepCard
            :step-number="3"
            title="法务审查"
            :completed="pipeline.steps.compliance.completed"
            :loading="pipeline.steps.compliance.loading"
            :active="pipeline.activeStep === 'compliance'"
            @toggle="pipeline.setActiveStep('compliance')"
          >
            <ComplianceCheckStep />
          </StepCard>

          <StepCard
            :step-number="4"
            title="语音合成"
            :completed="pipeline.steps.synthesize.completed"
            :loading="pipeline.steps.synthesize.loading"
            :active="pipeline.activeStep === 'synthesize'"
            @toggle="pipeline.setActiveStep('synthesize')"
          >
            <AudioSynthesizeStep />
          </StepCard>

          <StepCard
            :step-number="5"
            title="数字人生成"
            :completed="pipeline.steps.avatar.completed"
            :loading="pipeline.steps.avatar.loading"
            :active="pipeline.activeStep === 'avatar'"
            @toggle="pipeline.setActiveStep('avatar')"
          >
            <AvatarGenerateStep />
          </StepCard>

          <StepCard
            :step-number="6"
            title="视频后期"
            :completed="pipeline.steps.postprod.completed"
            :loading="pipeline.steps.postprod.loading"
            :active="pipeline.activeStep === 'postprod'"
            @toggle="pipeline.setActiveStep('postprod')"
          >
            <VideoPostStep />
          </StepCard>

          <StepCard
            :step-number="7"
            title="发布"
            :completed="pipeline.steps.publish.completed"
            :loading="pipeline.steps.publish.loading"
            :active="pipeline.activeStep === 'publish'"
            @toggle="pipeline.setActiveStep('publish')"
          >
            <PublishStep />
          </StepCard>
        </div>
      </div>
    </div>

    <!-- Preview panel -->
    <div class="preview-section">
      <PreviewPanel />
    </div>
  </div>
</template>

<style scoped>
.home-view {
  display: flex;
  flex: 1;
  height: 100vh;
  overflow: hidden;
}

.editor-panel {
  width: var(--editor-width);
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border-light);
  background: var(--color-bg-page);
  flex-shrink: 0;
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5) var(--space-6);
  border-bottom: 1px solid var(--color-border-light);
  flex-shrink: 0;
}

.editor-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.step-progress {
  padding: var(--space-1) var(--space-3);
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: var(--text-xs);
  border-radius: var(--radius-full);
  font-weight: var(--font-medium);
}

.editor-scroll {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-5) var(--space-5);
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-bottom: var(--space-10);
}

.preview-section {
  flex: 1;
  background: var(--color-bg-page);
  overflow: hidden;
  display: flex;
  justify-content: center;
}
</style>
