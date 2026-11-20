import { useState, useRef, useEffect } from 'react'
import {
  createPaymentOrder,
  getUserCredits,
  routeRequest,
  verifyPayment,
} from '../services/api'
import CodeBlock from '../components/CodeBlock'
import './Chat.css'

const AGENTS = [
  { id: 'auto', label: 'Auto-Route', icon: '🧠', desc: 'AI picks the best agent' },
  { id: 'code', label: 'Code', icon: '💻', desc: 'Generate & fix code', cost: 5 },
  { id: 'pdf', label: 'PDF', icon: '📄', desc: 'Analyze documents', cost: 2 },
  { id: 'ppt', label: 'PPT', icon: '📊', desc: 'Create presentations', cost: 3 },
  { id: 'image', label: 'Image', icon: '🎨', desc: 'Generate images', cost: 5 },
  { id: 'video', label: 'Video', icon: '🎥', desc: 'Create videos', cost: 10 },
  { id: 'chat', label: 'Chat', icon: '💬', desc: 'General conversation', cost: 1 },
]

function loadRazorpayCheckout() {
  if (window.Razorpay) return Promise.resolve()

  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = resolve
    script.onerror = () => reject(new Error('Could not load Razorpay checkout'))
    document.body.appendChild(script)
  })
}

function Chat({ user, setUser, onLogout }) {
  const [conversations, setConversations] = useState([
    { id: 1, title: 'New chat', messages: [] }
  ])
  const [activeConvId, setActiveConvId] = useState(1)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [credits, setCredits] = useState(user.credit_balance || 100)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [agentMenuOpen, setAgentMenuOpen] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState(AGENTS[0])
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [paymentLoading, setPaymentLoading] = useState(false)
  const [paymentError, setPaymentError] = useState('')
  const messagesEndRef = useRef(null)
  const textareaRef = useRef(null)
  const agentMenuRef = useRef(null)

  const activeConv = conversations.find(c => c.id === activeConvId)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeConv?.messages])

  useEffect(() => {
    refreshCredits()
  }, [])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (agentMenuRef.current && !agentMenuRef.current.contains(e.target)) {
        setAgentMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const refreshCredits = async () => {
    try {
      const data = await getUserCredits()
      setCredits(data.balance)
    } catch (err) { /* skip */ }
  }

  const newChat = () => {
    const id = Date.now()
    setConversations(prev => [...prev, { id, title: 'New chat', messages: [] }])
    setActiveConvId(id)
    setInput('')
  }

  const deleteChat = (id) => {
    if (conversations.length === 1) {
      const newConversation = { id: Date.now(), title: 'New chat', messages: [] }
      setConversations([newConversation])
      setActiveConvId(newConversation.id)
    } else {
      const filtered = conversations.filter(c => c.id !== id)
      setConversations(filtered)
      if (activeConvId === id) setActiveConvId(filtered[0].id)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = { role: 'user', content: input, agent: selectedAgent.id !== 'auto' ? selectedAgent : null }
    const prompt = input.trim()

    setConversations(prev => prev.map(c => {
      if (c.id !== activeConvId) return c
      const title = c.messages.length === 0 ? input.slice(0, 40) + (input.length > 40 ? '...' : '') : c.title
      return { ...c, title, messages: [...c.messages, userMsg] }
    }))

    setInput('')
    setLoading(true)

    try {
      const result = await routeRequest(prompt, selectedAgent.id)
      const botMsg = {
        role: 'assistant',
        content: result.response,
        destination: result.destination,
        creditsDeducted: result.credits_deducted,
        request: result.request,
      }
      setConversations(prev => prev.map(c =>
        c.id === activeConvId ? { ...c, messages: [...c.messages, botMsg] } : c
      ))
      setCredits(result.remaining_credits)
      const stored = JSON.parse(localStorage.getItem('cortex_user'))
      stored.credit_balance = result.remaining_credits
      localStorage.setItem('cortex_user', JSON.stringify(stored))
      setUser(stored)
    } catch (err) {
      if (err.response?.status === 401) {
        onLogout()
        return
      }

      const errMsg = {
        role: 'assistant',
        content: err.response?.data?.detail || 'Error: Could not process request. Check if backend is running.',
        isError: true,
      }
      setConversations(prev => prev.map(c =>
        c.id === activeConvId ? { ...c, messages: [...c.messages, errMsg] } : c
      ))
    } finally {
      setLoading(false)
    }
  }

  const handleBuyCredits = async () => {
    if (paymentLoading) return
    setPaymentError('')
    setPaymentLoading(true)

    try {
      const order = await createPaymentOrder('credits_50')
      await loadRazorpayCheckout()

      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: order.amount_paise,
        currency: order.currency,
        name: 'Cortex AI',
        description: `${order.credits} credits`,
        order_id: order.order_id,
        prefill: { name: user.username, email: user.email },
        handler: async (payment) => {
          try {
            const result = await verifyPayment(payment)
            const updatedUser = { ...user, credit_balance: result.balance }
            setCredits(result.balance)
            setUser(updatedUser)
            localStorage.setItem('cortex_user', JSON.stringify(updatedUser))
            setPaymentError('')
            setPaymentLoading(false)
          } catch (err) {
            setPaymentError(err.response?.data?.detail || 'Payment verification failed. Contact support before retrying.')
            setPaymentLoading(false)
          }
        },
        modal: { ondismiss: () => setPaymentLoading(false) },
      })

      checkout.on('payment.failed', (event) => {
        setPaymentError(event.error?.description || 'Payment failed. No credits were added.')
        setPaymentLoading(false)
      })
      checkout.open()
    } catch (err) {
      setPaymentError(err.response?.data?.detail || err.message || 'Could not start checkout')
      setPaymentLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const autoResize = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 200) + 'px'
    }
  }

  const renderMessage = (msg, i) => {
    const isUser = msg.role === 'user'
    return (
      <div key={i} className={`msg-row ${isUser ? 'msg-user' : 'msg-bot'}`}>
        <div className="msg-avatar">
          {isUser ? (
            <div className="avatar-user">{user.username?.[0]?.toUpperCase() || 'U'}</div>
          ) : (
            <div className="avatar-bot">
              <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
                <circle cx="20" cy="20" r="18" stroke="#10a37f" strokeWidth="3"/>
                <path d="M14 20 L18 24 L26 16" stroke="#10a37f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          )}
        </div>
        <div className="msg-body">
          <div className="msg-name">
            {isUser ? 'You' : 'Cortex AI'}
            {!isUser && msg.destination && (
              <span className="msg-agent-badge">{msg.destination.toUpperCase()} Agent</span>
            )}
            {msg.agent && <span className="msg-agent-badge">{msg.agent.icon} {msg.agent.label}</span>}
          </div>
          <div className={`msg-content ${msg.isError ? 'msg-error' : ''}`}>
            {renderContent(msg.content)}
          </div>
          {!isUser && msg.creditsDeducted && (
            <div className="msg-meta">-{msg.creditsDeducted} credits used</div>
          )}
        </div>
      </div>
    )
  }

  const renderContent = (text) => {
    if (!text) return null
    // Split by code blocks  ```lang\ncode\n```
    const parts = text.split(/(```[\s\S]*?```)/g)
    return parts.map((part, i) => {
      const codeMatch = part.match(/```(\w*)\n?([\s\S]*?)```/)
      if (codeMatch) {
        return <CodeBlock key={i} language={codeMatch[1] || 'text'} code={codeMatch[2].trim()} />
      }
      // Inline code
      const inlineParts = part.split(/(`[^`]+`)/g)
      return (
        <span key={i}>
          {inlineParts.map((ip, j) => {
            if (ip.startsWith('`') && ip.endsWith('`')) {
              return <code key={j} className="inline-code">{ip.slice(1, -1)}</code>
            }
            return ip
          })}
        </span>
      )
    })
  }

  return (
    <div className="chat-layout">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-top">
          <button className="new-chat-btn" onClick={newChat}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            New chat
          </button>
        </div>

        <div className="sidebar-chats">
          {conversations.map(c => (
            <div
              key={c.id}
              className={`chat-item ${c.id === activeConvId ? 'active' : ''}`}
              onClick={() => setActiveConvId(c.id)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>
              <span className="chat-item-title">{c.title}</span>
              <button className="chat-delete" onClick={(e) => { e.stopPropagation(); deleteChat(c.id) }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/></svg>
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom">
          <button
            className="credit-display"
            onClick={handleBuyCredits}
            disabled={paymentLoading}
            title="Buy 50 credits for INR 50"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            <span>{credits} credits</span>
            <span className="recharge-hint">{paymentLoading ? 'Opening...' : '+ 50 for INR 50'}</span>
          </button>
          {paymentError && <div className="payment-error" role="alert">{paymentError}</div>}
          <div className="user-section">
            <button className="user-btn" onClick={() => setShowUserMenu(!showUserMenu)}>
              <div className="avatar-user small">{user.username?.[0]?.toUpperCase() || 'U'}</div>
              <span>{user.username}</span>
            </button>
            {showUserMenu && (
              <div className="user-dropdown">
                <div className="dropdown-info">{user.email}</div>
                <button onClick={onLogout} className="dropdown-item logout">Log out</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="chat-main">
        {/* Top bar */}
        <div className="chat-topbar">
          <button className="toggle-sidebar" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
          </button>
          <span className="topbar-title">Cortex AI</span>
          <div className="topbar-agent">
            {selectedAgent.icon} {selectedAgent.label}
          </div>
        </div>

        {/* Messages */}
        <div className="messages-container">
          {activeConv?.messages.length === 0 ? (
            <div className="empty-state">
              <div className="empty-logo">
                <svg width="48" height="48" viewBox="0 0 40 40" fill="none">
                  <circle cx="20" cy="20" r="18" stroke="#3e3e3e" strokeWidth="2"/>
                  <path d="M14 20 L18 24 L26 16" stroke="#10a37f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <h2>What can I help with?</h2>
              <div className="suggestions">
                <button onClick={() => setInput('Write a Python function to sort a list using merge sort')}>
                  <span className="suggestion-icon">💻</span>
                  <span>Write a merge sort in Python</span>
                </button>
                <button onClick={() => setInput('Create a PowerPoint presentation outline about Climate Change')}>
                  <span className="suggestion-icon">📊</span>
                  <span>Presentation on Climate Change</span>
                </button>
                <button onClick={() => setInput('Explain quantum computing in simple terms')}>
                  <span className="suggestion-icon">💬</span>
                  <span>Explain quantum computing</span>
                </button>
                <button onClick={() => setInput('Generate a 4K wallpaper of a cyberpunk city')}>
                  <span className="suggestion-icon">🎨</span>
                  <span>Generate cyberpunk wallpaper</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="messages-list">
              {activeConv.messages.map((msg, i) => renderMessage(msg, i))}
              {loading && (
                <div className="msg-row msg-bot">
                  <div className="msg-avatar">
                    <div className="avatar-bot">
                      <svg width="20" height="20" viewBox="0 0 40 40" fill="none">
                        <circle cx="20" cy="20" r="18" stroke="#10a37f" strokeWidth="3"/>
                        <path d="M14 20 L18 24 L26 16" stroke="#10a37f" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </div>
                  </div>
                  <div className="msg-body">
                    <div className="msg-name">Cortex AI</div>
                    <div className="typing-indicator">
                      <span></span><span></span><span></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="input-area">
          <form onSubmit={handleSubmit} className="input-form">
            <div className="input-wrapper">
              {/* Agent selector */}
              <div className="agent-selector" ref={agentMenuRef}>
                <button type="button" className="agent-toggle" onClick={() => setAgentMenuOpen(!agentMenuOpen)}>
                  <span>{selectedAgent.icon}</span>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="6 9 12 15 18 9"/></svg>
                </button>
                {agentMenuOpen && (
                  <div className="agent-dropdown">
                    <div className="agent-dropdown-title">Choose an agent</div>
                    {AGENTS.map(a => (
                      <button
                        key={a.id}
                        type="button"
                        className={`agent-option ${selectedAgent.id === a.id ? 'selected' : ''}`}
                        onClick={() => { setSelectedAgent(a); setAgentMenuOpen(false) }}
                      >
                        <span className="agent-opt-icon">{a.icon}</span>
                        <div className="agent-opt-info">
                          <span className="agent-opt-label">{a.label}</span>
                          <span className="agent-opt-desc">{a.desc}</span>
                        </div>
                        {a.cost && <span className="agent-opt-cost">{a.cost} cr</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => { setInput(e.target.value); autoResize() }}
                onKeyDown={handleKeyDown}
                placeholder="Message Cortex AI..."
                rows={1}
                disabled={loading}
              />

              <button type="submit" className="send-btn" disabled={!input.trim() || loading}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
              </button>
            </div>
          </form>
          <div className="input-footer">
            Cortex AI can make mistakes. Check important info.
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat
