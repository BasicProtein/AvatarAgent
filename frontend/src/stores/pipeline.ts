import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type StepName = 'extract' | 'rewrite' | 'synthesize' | 'avatar' | 'postprod' | 'publish'

export interface StepData {
    completed: boolean
    loading: boolean
    result: Record<string, unknown> | null
}

export const usePipelineStore = defineStore('pipeline', () => {
    const activeStep = ref<StepName>('extract')

    const steps = ref<Record<StepName, StepData>>({
        extract: { completed: false, loading: false, result: null },
        rewrite: { completed: false, loading: false, result: null },
        synthesize: { completed: false, loading: false, result: null },
        avatar: { completed: false, loading: false, result: null },
        postprod: { completed: false, loading: false, result: null },
        publish: { completed: false, loading: false, result: null },
    })

    // Extracted script text
    const extractedText = ref('')
    // Rewritten script text
    const rewrittenText = ref('')
    // Generated description
    const description = ref('')
    // Synthesized audio path
    const audioPath = ref('')
    // Avatar video path
    const avatarVideoPath = ref('')
    // Final video path (after post-production)
    const finalVideoPath = ref('')
    // Cover image path
    const coverPath = ref('')

    const completedCount = computed(() =>
        Object.values(steps.value).filter((s) => s.completed).length
    )

    function setActiveStep(step: StepName) {
        activeStep.value = step
    }

    function setStepLoading(step: StepName, loading: boolean) {
        steps.value[step].loading = loading
    }

    function completeStep(step: StepName, result: Record<string, unknown> | null = null) {
        steps.value[step].completed = true
        steps.value[step].loading = false
        steps.value[step].result = result
    }

    function resetStep(step: StepName) {
        steps.value[step] = { completed: false, loading: false, result: null }
    }

    function resetAll() {
        for (const key of Object.keys(steps.value) as StepName[]) {
            resetStep(key)
        }
        extractedText.value = ''
        rewrittenText.value = ''
        description.value = ''
        audioPath.value = ''
        avatarVideoPath.value = ''
        finalVideoPath.value = ''
        coverPath.value = ''
        activeStep.value = 'extract'
    }

    return {
        activeStep,
        steps,
        extractedText,
        rewrittenText,
        description,
        audioPath,
        avatarVideoPath,
        finalVideoPath,
        coverPath,
        completedCount,
        setActiveStep,
        setStepLoading,
        completeStep,
        resetStep,
        resetAll,
    }
})
