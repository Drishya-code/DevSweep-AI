import { useState, useRef, useEffect } from 'react'
import { cn, generateId } from '../utils/helpers'
import { useDevSweep } from '../context/DevSweepContext'
import {
  Bot,
  Send,
  Loader2,
  Sparkles,
  Trash2,
  FileText,
  RotateCcw,
  Search,
  Copy,
  X,
} from 'lucide-react'
import { ChatMessage } from '../types/api'

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: generateId(),
    role: 'assistant',
    content: `Welcome to DevSweep AI Agent! 👋

I can help you:
• **Scan** your workspace for cleanup opportunities
• **Analyze** project structure and detect regenerable artifacts
• **Create** safe cleanup plans with risk assessments
• **Execute** approved cleanups with verification
• **Restore** cleaned environments later

Try saying:
- "Scan my React project"
- "Clean up node_modules and build folders"
- "Show me what's safe to delete"
- "How do I restore my project after cleanup?"

What would you like to do?`,
    timestamp: new Date(),
  },
]

const QUICK_ACTIONS = [
  { label: 'Scan Workspace', icon: Search, prompt: 'Scan my current workspace for cleanup opportunities' },
  { label: 'Create Cleanup Plan', icon: FileText, prompt: 'Create a cleanup plan for my project' },
  { label: 'Restore Project', icon: RotateCcw, prompt: 'How do I restore my project after cleanup?' },
  { label: 'Safe Cleanup', icon: Trash2, prompt: 'Clean only SAFE items (node_modules, dist, caches)' },
]

export function AIAgent() {
  const { currentProject, aiProvider, aiModel } = useDevSweep()
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return

    const userMessage: ChatMessage = {
      id: generateId(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    const userInput = input
    setInput('')
    setIsLoading(true)

    try {
      // Call real backend AI API
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userInput,
          history: messages.slice(-10).map(m => ({ role: m.role, content: m.content })),
          project_path: currentProject?.project_path,
          access_grant_id: currentProject?.access_grant_id,
        }),
      })
      
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'AI request failed')
      }
      
      const data = await res.json()
      
      const assistantMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
      }
      
      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: generateId(),
        role: 'assistant',
        content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickAction = (prompt: string) => {
    setInput(prompt)
    textareaRef.current?.focus()
  }

  return (
    <div className="h-full flex flex-col animate-in">
      <div className="flex items-center justify-between border-b border-devsweep-border p-4 bg-devsweep-bgSecondary">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-devsweep-accent/10 rounded-lg flex items-center justify-center">
            <Bot className="w-5 h-5 text-devsweep-accent" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">DevSweep AI Agent</h1>
            <p className="text-xs text-devsweep-textMuted">{aiProvider} • {aiModel}</p>
          </div>
        </div>
        {currentProject && (
          <div className="text-right text-sm">
            <p className="font-medium">{currentProject.project_path.split('/').pop()}</p>
            <p className="text-devsweep-textMuted">{currentProject.framework} • {currentProject.total_recoverable_human} recoverable</p>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={messagesEndRef}>
        {messages.map((message) => (
          <div key={message.id} className={cn('flex gap-3', message.role === 'user' && 'flex-row-reverse')}>
            <div className={cn('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0', 
              message.role === 'assistant' ? 'bg-devsweep-accent/10 text-devsweep-accent' : 'bg-devsweep-bgTertiary text-devsweep-textSecondary'
            )}>
              {message.role === 'assistant' ? <Bot className="w-4 h-4" /> : <span className="text-xs font-medium">U</span>}
            </div>
            <div className={cn('max-w-[80%] px-4 py-3 rounded-2xl', 
              message.role === 'assistant' ? 'bg-devsweep-bgSecondary border border-devsweep-border text-devsweep-text' : 'bg-devsweep-accent text-devsweep-bg'
            )}>
              <div className="prose prose-sm dark prose-invert max-w-none">{message.content}</div>
              <div className="flex items-center justify-end gap-2 mt-2">
                <span className="text-xs text-devsweep-textMuted">{message.timestamp.toLocaleTimeString()}</span>
                {message.role === 'assistant' && (
                  <button className="p-1 hover:bg-devsweep-bgTertiary rounded transition-colors" title="Copy">
                    <Copy className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 bg-devsweep-accent/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-devsweep-accent" />
            </div>
            <div className="bg-devsweep-bgSecondary border border-devsweep-border rounded-2xl px-4 py-3 max-w-[80%]">
              <div className="flex items-center gap-2 text-devsweep-textMuted">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>AI is analyzing...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-devsweep-border p-4 bg-devsweep-bgSecondary">
        <div className="flex flex-wrap gap-2 mb-3">
          {QUICK_ACTIONS.map((action, i) => (
            <button
              key={i}
              onClick={() => handleQuickAction(action.prompt)}
              disabled={isLoading}
              className="px-3 py-1.5 text-xs bg-devsweep-bg border border-devsweep-border rounded-lg hover:border-devsweep-accent/50 transition-colors flex items-center gap-1.5"
            >
              <action.icon className="w-3 h-3" />
              {action.label}
            </button>
          ))}
        </div>
        <form onSubmit={handleSend} className="flex gap-2">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask DevSweep anything about cleanup, restore, or project analysis..."
            className="flex-1 px-4 py-2 bg-devsweep-bg border border-devsweep-border rounded-lg text-devsweep-text placeholder-devsweep-textMuted focus:border-devsweep-accent focus:outline-none focus:ring-1 focus:ring-devsweep-accent resize-none min-h-[44px] max-h-32"
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-4 py-2 bg-devsweep-accent text-devsweep-bg rounded-lg font-medium hover:bg-devsweep-accentHover transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 self-end mb-1"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </form>
      </div>
    </div>
  )
}
