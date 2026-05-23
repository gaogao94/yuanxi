import { describe, it, expect, vi, beforeEach } from 'vitest'
import { sendMessageStream } from '../app/services/chatApi'
import type { ApiStreamEvent } from '../app/types/api'

function createSSEResponse(events: { event: string; data: object }[]): Response {
  const body = events
    .map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
    .join('')

  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(body))
      controller.close()
    },
  })

  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

describe('sendMessageStream — SSE 解析', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('逐条解析 thinking 事件', async () => {
    const events: ApiStreamEvent[] = []

    const response = createSSEResponse([
      { event: 'thinking', data: { text: '正在接收问题...', source: 'Workflow' } },
      { event: 'thinking', data: { text: '正在查询图谱...', source: 'Agent1' } },
      { event: 'done', data: {} },
    ])

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response)

    const stream = sendMessageStream('test')
    for await (const event of stream) {
      events.push(event)
    }

    expect(events.length).toBeGreaterThanOrEqual(2)
    expect(events[0].type).toBe('thinking')
    expect((events[0].data as any).text).toBe('正在接收问题...')
    expect((events[0].data as any).source).toBe('Workflow')
    expect(events[1].type).toBe('thinking')
    expect((events[1].data as any).source).toBe('Agent1')
  })

  it('解析 clarification 事件并携带 conversation_id', async () => {
    const events: ApiStreamEvent[] = []
    const clarificationData = {
      status: 'needs_clarification',
      conversation_id: 'conv-123',
      text: '请确认指标',
      clarification_questions: [
        { id: 'metric', question: '请选择指标', type: 'single_select', options: ['转化率', '复诊率'], required: true, source: 'graph' },
      ],
    }

    const response = createSSEResponse([
      { event: 'thinking', data: { text: '正在分析...' } },
      { event: 'clarification', data: clarificationData },
      { event: 'done', data: {} },
    ])

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response)

    const stream = sendMessageStream('test')
    for await (const event of stream) {
      events.push(event)
    }

    const clarification = events.find((e) => e.type === 'clarification')
    expect(clarification).toBeDefined()
    expect((clarification!.data as any).conversation_id).toBe('conv-123')
    expect((clarification!.data as any).clarification_questions.length).toBe(1)
    expect((clarification!.data as any).clarification_questions[0].options).toEqual(['转化率', '复诊率'])
  })

  it('解析 result 完成事件', async () => {
    const events: ApiStreamEvent[] = []
    const resultData = {
      status: 'completed',
      conversation_id: 'conv-456',
      text: '分析完成',
      clarification_questions: [],
      thinking: [{ text: '[Agent1] done', source: 'Agent1' }],
      charts: [],
      attachments: [],
    }

    const response = createSSEResponse([
      { event: 'thinking', data: { text: '执行中...' } },
      { event: 'result', data: resultData },
      { event: 'done', data: {} },
    ])

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response)

    const stream = sendMessageStream('test')
    for await (const event of stream) {
      events.push(event)
    }

    const result = events.find((e) => e.type === 'result')
    expect(result).toBeDefined()
    expect((result!.data as any).status).toBe('completed')
    expect((result!.data as any).conversation_id).toBe('conv-456')
  })

  it('解析 error 事件', async () => {
    const events: ApiStreamEvent[] = []
    const response = createSSEResponse([
      { event: 'error', data: { text: '工作流执行失败: timeout' } },
      { event: 'done', data: {} },
    ])

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(response)

    const stream = sendMessageStream('test')
    for await (const event of stream) {
      events.push(event)
    }

    const error = events.find((e) => e.type === 'error')
    expect(error).toBeDefined()
    expect((error!.data as any).text).toContain('timeout')
  })

  it('fetch 失败时抛出异常', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    const stream = sendMessageStream('test')
    await expect(async () => {
      for await (const _event of stream) {
        // consume
      }
    }).rejects.toThrow('Network error')
  })
})
