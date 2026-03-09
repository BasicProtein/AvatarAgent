import client from './client'

export interface ExtractRequest {
    video_url: string
}

export interface RewriteRequest {
    text: string
    api_key: string
    mode: 'auto' | 'custom'
    prompt?: string
}

export interface DescriptionRequest {
    text: string
    api_key: string
}

export interface ComplianceCheckRequest {
    text: string
    api_key: string
}

export interface ProhibitedWordItem {
    word: string
    position: number
    category: string
}

export interface AiSuggestionItem {
    original: string
    suggestion: string
    reason: string
}

export interface ComplianceCheckResponse {
    passed: boolean
    prohibited_words: ProhibitedWordItem[]
    ai_suggestions: AiSuggestionItem[]
    revised_text: string
}

export const scriptApi = {
    extract: (data: ExtractRequest) =>
        client.post<{ text: string }>('/api/script/extract', data),

    rewrite: (data: RewriteRequest) =>
        client.post<{ text: string }>('/api/script/rewrite', data),

    generateDescription: (data: DescriptionRequest) =>
        client.post<{ text: string }>('/api/script/description', data),

    complianceCheck: (data: ComplianceCheckRequest) =>
        client.post<ComplianceCheckResponse>('/api/script/compliance-check', data),
}
