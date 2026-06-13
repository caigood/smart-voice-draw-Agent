import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import './App.css'

function App() {
  const [status, setStatus] = useState('idle')
  const [currentImage, setCurrentImage] = useState(null)
  const [currentPrompt, setCurrentPrompt] = useState('')
  const [optimizedPrompt, setOptimizedPrompt] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'agent',
      content: '我是你的智能语音生图小助手，有什么图片是你想生成的么，请直接语音告诉我！',
      timestamp: new Date().toISOString()
    }
  ])
  const [history, setHistory] = useState([])
  const [previewImage, setPreviewImage] = useState(null)
  const [pendingQuestion, setPendingQuestion] = useState(null)
  const [pendingPrompt, setPendingPrompt] = useState('')
  const [pendingAction, setPendingAction] = useState(null)
  const [lastUserText, setLastUserText] = useState('')
  
  const recognitionRef = useRef(null)
  const synthRef = useRef(window.speechSynthesis)
  const messagesEndRef = useRef(null)
  const pendingActionRef = useRef(null)
  const pendingPromptRef = useRef('')
  const currentPromptRef = useRef('')
  const pendingQuestionRef = useRef(null)
  const historyRef = useRef([])
  const currentImageRef = useRef(null)

  useEffect(() => {
    pendingActionRef.current = pendingAction
    pendingPromptRef.current = pendingPrompt
    currentPromptRef.current = currentPrompt
    pendingQuestionRef.current = pendingQuestion
    historyRef.current = history
    currentImageRef.current = currentImage
  }, [pendingAction, pendingPrompt, currentPrompt, pendingQuestion, history, currentImage])

  // 初始化语音识别
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.lang = 'zh-CN'
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false

      recognitionRef.current.onresult = async (event) => {
        const transcript = event.results[0][0].transcript
        setLastUserText(transcript)
        setStatus('thinking')
        await handleUserInput(transcript)
      }

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        setStatus('idle')
        if (pendingActionRef.current === 'confirm_generate' && pendingPromptRef.current) {
          const message = '我没有听清你的确认回复，请说“可以生成”或“重新调整”。'
          addMessage('agent', message)
          speak(message)
          return
        }
        addMessage('agent', '语音识别失败，请重试。')
      }

      recognitionRef.current.onend = () => {
        if (status === 'listening') {
          setStatus('idle')
        }
      }
    } else {
      console.warn('Speech recognition not supported')
    }
  }, [])

  // 自动滚动到最新消息
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 添加消息
  const addMessage = (role, content) => {
    setMessages(prev => [...prev, { role, content, timestamp: new Date().toISOString() }])
  }

  // 语音播报
  const speak = (text) => {
    if (synthRef.current) {
      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      utterance.rate = 1.0
      synthRef.current.speak(utterance)
    }
  }

  // 下载历史图片
  const downloadImage = async (imageUrl, versionName) => {
    try {
      const response = await fetch(imageUrl)
      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = `${versionName}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(objectUrl)
    } catch (error) {
      console.error('Download failed:', error)
      window.open(imageUrl, '_blank')
    }
  }

  // 处理用户输入
  const handleUserInput = async (text) => {
    try {
      addMessage('user', text)

      const activePendingAction = pendingActionRef.current
      const activePendingPrompt = pendingPromptRef.current

      if (activePendingAction === 'confirm_generate' && activePendingPrompt) {
        const confirmResponse = await axios.post('/api/agent/confirm', {
          text,
          pendingPrompt: activePendingPrompt,
          sessionState: {
            currentPrompt: currentPromptRef.current,
            pendingQuestion: pendingQuestionRef.current,
            history: historyRef.current
          }
        })

        const confirmResult = confirmResponse.data

        if (confirmResult.confirmIntent === 'confirm' && confirmResult.shouldGenerate) {
          const promptToGenerate = confirmResult.newPrompt || activePendingPrompt
          setPendingPrompt('')
          setPendingAction(null)
          pendingActionRef.current = null
          pendingPromptRef.current = ''
          addMessage('agent', confirmResult.agentReply || '好的，正在使用该提示词生成图片。')
          speak(confirmResult.agentReply || '好的，正在使用该提示词生成图片。')
          await generateImage(promptToGenerate)
          setStatus('idle')
          return
        }

        if (confirmResult.confirmIntent === 'revise' && confirmResult.newPrompt) {
          setPendingPrompt(confirmResult.newPrompt)
          setPendingAction('confirm_generate')
          pendingPromptRef.current = confirmResult.newPrompt
          pendingActionRef.current = 'confirm_generate'
          setOptimizedPrompt(confirmResult.newPrompt)
          const message = `${confirmResult.agentReply || '我已根据你的反馈更新提示词。'} 新提示词是：${confirmResult.newPrompt}。请确认是否使用这个修改后的提示词生成图片？你可以说“可以生成”，也可以继续说出要调整的地方。`
          addMessage('agent', message)
          speak('我已根据你的反馈更新提示词，请确认是否使用这个修改后的提示词生成图片？')
          setStatus('idle')
          return
        }

        setPendingAction(null)
        setPendingPrompt('')
        pendingActionRef.current = null
        pendingPromptRef.current = ''
        addMessage('agent', confirmResult.agentReply || '好的，请重新描述你的绘图需求。')
        speak(confirmResult.agentReply || '好的，请重新描述你的绘图需求。')
        setStatus('idle')
        return
      }

      // 调用后端解析
      const parseResponse = await axios.post('/api/agent/parse', {
        text,
        sessionState: {
          currentPrompt: currentPromptRef.current,
          pendingQuestion: pendingQuestionRef.current,
          history: historyRef.current
        }
      })

      const result = parseResponse.data

      // 显示智能体回复
      addMessage('agent', result.agentReply)
      speak(result.agentReply)

      // 处理不同意图
      switch (result.intent) {
        case 'undo':
          handleUndo()
          break
        case 'clear':
          handleClear()
          break
        case 'regenerate':
          if (currentPromptRef.current) {
            await generateImage(currentPromptRef.current)
          }
          break
        case 'clarify_answer':
        case 'create_image':
          if (result.needClarification) {
            setPendingQuestion(result.clarificationQuestion)
            addMessage('agent', result.clarificationQuestion)
            speak(result.clarificationQuestion)
          } else if (result.prompt) {
            setOptimizedPrompt(result.prompt)
            setPendingPrompt(result.prompt)
            setPendingAction('confirm_generate')
            pendingPromptRef.current = result.prompt
            pendingActionRef.current = 'confirm_generate'
            setPendingQuestion(null)
            const confirmMessage = `我优化后的提示词是：${result.prompt}。是否使用这个提示词生成图片？你可以说“是”或“可以”，也可以说“不要，重新调整”。`
            addMessage('agent', confirmMessage)
            speak('我已经优化好提示词，是否使用这个提示词生成图片？')
          }
          break
        case 'edit_image':
          if (result.needClarification) {
            setPendingQuestion(result.clarificationQuestion)
            addMessage('agent', result.clarificationQuestion)
            speak(result.clarificationQuestion)
          } else if (!currentImageRef.current) {
            addMessage('agent', '当前没有可修改的图片，请先生成一张图片。')
            speak('当前没有可修改的图片，请先生成一张图片。')
          } else {
            setOptimizedPrompt(text)
            setPendingQuestion(null)
            await editImage(currentImageRef.current, text)
          }
          break
        default:
          addMessage('agent', '我没有理解这个指令，请换一种说法。')
      }

      setStatus('idle')
    } catch (error) {
      console.error('Error processing input:', error)
      setStatus('idle')
      addMessage('agent', '处理失败，请重试。')
      speak('处理失败，请重试。')
    }
  }

  // 生成图片
  const generateImage = async (prompt) => {
    try {
      setStatus('generating')
      addMessage('agent', '正在生成图片...')
      
      const response = await axios.post('/api/image/generate', {
        prompt,
        negativePrompt: '低清晰度，模糊，文字水印'
      })

      const imageUrl = response.data.imageUrl
      const versionId = response.data.versionId

      setCurrentImage(imageUrl)
      setCurrentPrompt(prompt)
      currentImageRef.current = imageUrl
      currentPromptRef.current = prompt

      // 添加到历史记录
      const newVersion = {
        id: versionId,
        imageUrl,
        prompt,
        userText: lastUserText,
        createdAt: new Date().toISOString()
      }
      setHistory(prev => {
        const next = [...prev, newVersion]
        historyRef.current = next
        return next
      })

      setStatus('completed')
      addMessage('agent', '图片生成完成。')
      speak('图片生成完成。')
      
      setTimeout(() => setStatus('idle'), 1000)
    } catch (error) {
      console.error('Error generating image:', error)
      setStatus('error')
      addMessage('agent', '图片生成失败，请稍后重试。')
      speak('图片生成失败，请稍后重试。')
      setTimeout(() => setStatus('idle'), 1000)
    }
  }

  // 基于当前图片进行编辑
  const editImage = async (imageUrl, prompt) => {
    try {
      setStatus('generating')
      addMessage('agent', '正在基于当前图片进行修改...')
      
      const response = await axios.post('/api/image/edit', {
        imageUrl,
        prompt,
        negativePrompt: ''
      })

      const newImageUrl = response.data.imageUrl
      const versionId = response.data.versionId

      setCurrentImage(newImageUrl)
      setCurrentPrompt(prompt)
      currentImageRef.current = newImageUrl
      currentPromptRef.current = prompt

      const newVersion = {
        id: versionId,
        imageUrl: newImageUrl,
        prompt,
        userText: lastUserText,
        createdAt: new Date().toISOString(),
        type: 'edit'
      }
      setHistory(prev => {
        const next = [...prev, newVersion]
        historyRef.current = next
        return next
      })

      setStatus('completed')
      addMessage('agent', '图片修改完成。')
      speak('图片修改完成。')
      
      setTimeout(() => setStatus('idle'), 1000)
    } catch (error) {
      console.error('Error editing image:', error)
      setStatus('error')
      const detail = error.response?.data?.detail || '图片修改失败，请稍后重试。'
      addMessage('agent', detail)
      speak('图片修改失败，请稍后重试。')
      setTimeout(() => setStatus('idle'), 1000)
    }
  }

  // 回退版本
  const handleUndo = () => {
    const activeHistory = historyRef.current
    if (activeHistory.length > 1) {
      const newHistory = activeHistory.slice(0, -1)
      setHistory(newHistory)
      historyRef.current = newHistory
      const lastVersion = newHistory[newHistory.length - 1]
      setCurrentImage(lastVersion.imageUrl)
      setCurrentPrompt(lastVersion.prompt)
      currentImageRef.current = lastVersion.imageUrl
      currentPromptRef.current = lastVersion.prompt
      addMessage('agent', '已恢复到上一张图片。')
      speak('已恢复到上一张图片。')
    } else {
      addMessage('agent', '没有更多历史版本了。')
      speak('没有更多历史版本了。')
    }
  }

  // 清空画布
  const handleClear = () => {
    setCurrentImage(null)
    setCurrentPrompt('')
    setOptimizedPrompt('')
    setHistory([])
    setPendingQuestion(null)
    setPendingPrompt('')
    setPendingAction(null)
    currentImageRef.current = null
    currentPromptRef.current = ''
    pendingQuestionRef.current = null
    historyRef.current = []
    pendingPromptRef.current = ''
    pendingActionRef.current = null
    addMessage('agent', '已清空当前作品，你可以描述新的绘图需求。')
    speak('已清空当前作品，你可以描述新的绘图需求。')
  }

  // 开始录音
  const startListening = () => {
    if (recognitionRef.current && status === 'idle') {
      setStatus('listening')
      recognitionRef.current.start()
      addMessage('agent', '正在聆听...')
    }
  }

  // 获取状态文本
  const getStatusText = () => {
    switch (status) {
      case 'idle': return '空闲'
      case 'listening': return '正在聆听'
      case 'recognizing': return '正在识别'
      case 'thinking': return '正在理解'
      case 'generating': return '正在生成'
      case 'completed': return '完成'
      case 'error': return '错误'
      default: return '空闲'
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>VoiceDraw Agent</h1>
        <p className="subtitle">纯语音 AI 绘图智能体</p>
        <div className="status-bar">
          <span className={`status-indicator ${status}`}></span>
          <span>状态：{getStatusText()}</span>
        </div>
      </header>

      <div className="main-content">
        <div className="image-section">
          <div className="image-container">
            {currentImage ? (
              <img src={currentImage} alt="Generated" className="generated-image" />
            ) : (
              <div className="placeholder">
                <p>图片展示区</p>
                <p className="hint">点击麦克风开始创作</p>
              </div>
            )}
          </div>
          {optimizedPrompt && (
            <div className="prompt-display">
              <h3>{pendingAction === 'confirm_generate' ? '待确认 Prompt' : '当前指令 / Prompt'}</h3>
              <p>{optimizedPrompt}</p>
            </div>
          )}
        </div>

        <div className="chat-section">
          <div className="messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`message ${msg.role}`}>
                {msg.role === 'agent' && <div className="agent-avatar">AI</div>}
                <div className="message-content">{msg.content}</div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      <div className="history-section">
        <h3>历史版本</h3>
        <div className="history-grid">
          {history.map((item, idx) => (
            <div key={idx} className="history-item">
              <img
                src={item.imageUrl}
                alt={`Version ${idx + 1}`}
                onClick={() => setPreviewImage(item.imageUrl)}
              />
              <span>v{idx + 1}</span>
              <button
                className="download-button"
                onClick={() => downloadImage(item.imageUrl, `voicedraw-v${idx + 1}`)}
              >
                下载
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="voice-control">
        <button
          className={`mic-button ${status === 'listening' ? 'active' : ''}`}
          onClick={startListening}
          disabled={status !== 'idle'}
        >
          {status === 'listening' ? '🎤 正在聆听...' : '🎤 点击说话'}
        </button>
        <div className="voice-hints">
          <p>你可以说：</p>
          <ul>
            <li>"画一只可爱的猫"</li>
            <li>"把背景改成夜晚"</li>
            <li>"给它加一顶蓝色帽子"</li>
            <li>"改成水彩风格但保留主体"</li>
            <li>"重新生成一张"</li>
            <li>"回到上一个版本"</li>
            <li>"清空画面"</li>
          </ul>
        </div>
      </div>

      {previewImage && (
        <div className="image-preview-overlay" onClick={() => setPreviewImage(null)}>
          <button className="image-preview-close" onClick={() => setPreviewImage(null)}>
            关闭
          </button>
          <img
            src={previewImage}
            alt="历史版本预览"
            className="image-preview-large"
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}

export default App
