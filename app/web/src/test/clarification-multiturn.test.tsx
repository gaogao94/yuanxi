/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Chat } from '../app/pages/Chat'
import type { ApiStreamEvent } from '../app/types/api'

vi.mock('../app/services/chatApi', () => ({
  sendMessageStream: vi.fn(),
}))

import { sendMessageStream } from '../app/services/chatApi'

const mockedStream = vi.mocked(sendMessageStream)

/** Create an async generator that yields the given events with optional delay. */
async function* yieldEvents(events: ApiStreamEvent[], delay = 10): AsyncGenerator<ApiStreamEvent, void, unknown> {
  for (const event of events) {
    if (delay > 0) {
      await new Promise((r) => setTimeout(r, delay))
    }
    yield event
  }
}

function mockStreamResponse(events: ApiStreamEvent[], delay = 10) {
  mockedStream.mockImplementationOnce(() => yieldEvents(events, delay))
}

describe('Chat — 多轮澄清', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('第一轮显示澄清问题，用户选择后发送第二轮', async () => {
    const user = userEvent.setup({ document: window.document })

    // Turn 1: needs_clarification
    mockStreamResponse([
      { type: 'thinking', data: { text: '正在分析...', source: 'Workflow' } },
      {
        type: 'clarification',
        data: {
          status: 'needs_clarification',
          conversation_id: 'conv-1',
          text: '请选择要分析的指标',
          clarification_questions: [
            {
              id: 'metric',
              question: '请选择指标',
              type: 'single_select',
              options: ['转化率：患者转化为会员的比例', '复诊率'],
              required: true,
              source: 'graph',
            },
          ],
        },
      },
    ])

    // Turn 2: completed
    mockStreamResponse([
      { type: 'thinking', data: { text: '执行分析...', source: 'Agent2' } },
      {
        type: 'result',
        data: {
          status: 'completed',
          conversation_id: 'conv-1',
          text: '分析完成：转化率 45.2%',
          clarification_questions: [],
          thinking: [{ text: '[Agent1] done', source: 'Agent1' }],
          charts: [],
          attachments: [],
        },
      },
    ])

    render(<Chat />)

    const input = screen.getByPlaceholderText('直接输入您的分析需求...')
    await user.type(input, '帮我看看最近门店转化怎么样')
    await user.click(screen.getByRole('button', { name: '' }))

    // Wait for clarification options to appear
    await waitFor(() => {
      expect(screen.getByText(/请选择要分析的指标/)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Click first clarification option
    const optionButton = await screen.findByText(/转化率：患者转化为会员的比例/)
    await user.click(optionButton)

    // Wait for final result
    await waitFor(() => {
      expect(screen.getByText(/分析完成：转化率 45.2%/)).toBeInTheDocument()
    }, { timeout: 5000 })
  })

  it('连续三轮澄清逐项消除追问', async () => {
    const user = userEvent.setup({ document: window.document })

    // Turn 1: metric + time + clinic
    mockStreamResponse([
      {
        type: 'clarification',
        data: {
          status: 'needs_clarification',
          conversation_id: 'conv-2',
          text: '请补充信息',
          clarification_questions: [
            { id: 'metric_definition', question: '请选择指标', type: 'free_text', options: [], required: true, source: 'user_input' },
            { id: 'time_range', question: '请选择时间范围', type: 'free_text', options: [], required: true, source: 'user_input' },
            { id: 'clinic_scope', question: '请选择门店', type: 'free_text', options: [], required: true, source: 'user_input' },
          ],
        },
      },
    ])

    // Turn 2: after metric, only time + clinic remain
    mockStreamResponse([
      {
        type: 'clarification',
        data: {
          status: 'needs_clarification',
          conversation_id: 'conv-2',
          text: '请补充信息',
          clarification_questions: [
            { id: 'time_range', question: '请选择时间范围', type: 'free_text', options: [], required: true, source: 'user_input' },
            { id: 'clinic_scope', question: '请选择门店', type: 'free_text', options: [], required: true, source: 'user_input' },
          ],
        },
      },
    ])

    // Turn 3: completed
    mockStreamResponse([
      {
        type: 'result',
        data: {
          status: 'completed',
          conversation_id: 'conv-2',
          text: '分析完成',
          clarification_questions: [],
          thinking: [],
          charts: [],
          attachments: [],
        },
      },
    ])

    render(<Chat />)

    // Turn 1: send question
    const input = screen.getByPlaceholderText('直接输入您的分析需求...')
    await user.type(input, '帮我分析门店数据')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getByText(/请选择指标/)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Wait for input to become enabled again (isSubmitting → false)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/请输入补充说明/)).not.toBeDisabled()
    }, { timeout: 5000 })

    // Turn 2: answer metric (free_text question, type into input)
    const clarifyingInput = screen.getByPlaceholderText(/请输入补充说明/)
    await user.type(clarifyingInput, '转化率')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getByText(/请选择时间范围/)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Wait for input to become enabled again
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/请输入补充说明/)).not.toBeDisabled()
    }, { timeout: 5000 })

    // Turn 3: answer time
    const clarifyingInput2 = screen.getByPlaceholderText(/请输入补充说明/)
    await user.type(clarifyingInput2, '最近一个月')
    await user.click(screen.getByRole('button', { name: '' }))

    await waitFor(() => {
      expect(screen.getAllByText(/分析完成/).length).toBeGreaterThan(0)
    }, { timeout: 5000 })

    expect(mockedStream.mock.calls.length).toBeGreaterThanOrEqual(3)
  })
})

describe('Chat — SSE 实时进度', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('thinking 步骤随 SSE 事件逐步追加', async () => {
    const user = userEvent.setup({ document: window.document })

    let capturedYield: ((event: ApiStreamEvent) => void) | null = null
    let generatorDone: (() => void) | null = null

    mockedStream.mockImplementationOnce(() => {
      const queue: ApiStreamEvent[] = []
      let waiting: ((result: IteratorResult<ApiStreamEvent, void>) => void) | null = null
      let done = false

      capturedYield = (event: ApiStreamEvent) => {
        if (waiting) {
          const resolve = waiting
          waiting = null
          resolve({ value: event, done: false })
        } else {
          queue.push(event)
        }
      }

      generatorDone = () => {
        done = true
        if (waiting) {
          const resolve = waiting
          waiting = null
          resolve({ value: undefined, done: true })
        }
      }

      return {
        [Symbol.asyncIterator]() {
          return this
        },
        async next(): Promise<IteratorResult<ApiStreamEvent, void>> {
          if (queue.length > 0) {
            return { value: queue.shift()!, done: false }
          }
          if (done) {
            return { value: undefined, done: true }
          }
          return new Promise((resolve) => {
            waiting = resolve
          })
        },
        async return(): Promise<IteratorResult<ApiStreamEvent, void>> {
          done = true
          return { value: undefined, done: true }
        },
      } as AsyncGenerator<ApiStreamEvent, void, unknown>
    })

    render(<Chat />)

    const input = screen.getByPlaceholderText('直接输入您的分析需求...')
    await user.type(input, '分析转化率')
    await user.click(screen.getByRole('button', { name: '' }))

    // Wait for the mock to be called (handleSubmit is async)
    await waitFor(() => {
      expect(capturedYield).not.toBeNull()
    }, { timeout: 3000 })

    // Emit thinking events one by one
    capturedYield!({ type: 'thinking', data: { text: '正在接收问题...', source: 'Workflow' } })

    await waitFor(() => {
      expect(screen.getByText(/正在接收问题/)).toBeInTheDocument()
    }, { timeout: 5000 })

    capturedYield!({ type: 'thinking', data: { text: '正在查询图谱...', source: 'Agent1' } })

    await waitFor(() => {
      expect(screen.getByText(/正在查询图谱/)).toBeInTheDocument()
    }, { timeout: 5000 })

    // Emit final result
    capturedYield!({
      type: 'result',
      data: {
        status: 'completed',
        conversation_id: 'conv-3',
        text: '最终分析结果',
        clarification_questions: [],
        thinking: [],
        charts: [],
        attachments: [],
      },
    })

    generatorDone!()

    await waitFor(() => {
      expect(screen.getByText(/最终分析结果/)).toBeInTheDocument()
    }, { timeout: 5000 })
  })
})
