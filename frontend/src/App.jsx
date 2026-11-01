import { useEffect, useRef, useState } from 'react'
import { Bot, Headphones, BrainCircuit, Send, RotateCcw, Sparkles, ShieldCheck, LoaderCircle, ChevronDown } from 'lucide-react'
const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '')
const DEMO_MODE = window.location.hostname.endsWith('github.io')
const BROWSER_DEMO = DEMO_MODE || !API
const newId = () => globalThis.crypto?.randomUUID?.() || `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
const starter = { support: "Hi! I’m your Customer Support Agent. I can help with delivery, refunds, account access, and order status. Try asking about order DEMO-1001.", interview: "Ready to practise? Choose your role and difficulty, then start your mock interview." }

function getDemoReply({ agent, message, role, difficulty, history }) {
  if (agent === 'support') {
    const text = message.toLowerCase()
    const escalated = ['lawyer', 'legal action', 'fraud', 'stolen card', 'safety issue', 'human agent', 'real person', 'supervisor']
      .some(trigger => text.includes(trigger))
    const orderId = message.toUpperCase().match(/\bDEMO-\d{4}\b/)?.[0]
    let reply

    if (escalated) {
      reply = "I understand this needs careful attention. I've flagged the conversation for human review. Please do not share passwords, verification codes, or full payment-card details."
    } else if (orderId === 'DEMO-1001') {
      reply = 'Your demo order is **shipped**. Estimated delivery: 2–3 business days. Tracking reference: TRACK-DEMO-1001.'
    } else if (orderId === 'DEMO-1002') {
      reply = 'Your demo order is **processing**. Estimated delivery: 3–5 business days.'
    } else if (orderId) {
      reply = 'I couldn’t locate that order in the demo data. Try DEMO-1001 or DEMO-1002.'
    } else if (['refund', 'return', 'money back'].some(term => text.includes(term))) {
      reply = 'Refund requests are reviewed within 3–5 business days after the returned item is received.'
    } else if (['password', 'login', 'sign in', 'account'].some(term => text.includes(term))) {
      reply = "Use 'Forgot password' on the sign-in screen. If you no longer have access to your email, a support specialist should verify your account."
    } else if (['shipping', 'delivery', 'tracking', 'order'].some(term => text.includes(term))) {
      reply = 'Standard delivery usually takes 3–5 business days. Tracking details are sent after the order ships.'
    } else if (['cancel', 'cancellation'].some(term => text.includes(term))) {
      reply = 'Orders can usually be cancelled before fulfilment. Share a demo order reference so I can check its status.'
    } else {
      reply = 'I can help with orders, delivery, refunds, cancellations, and account access. Could you share a little more detail? For order status, try DEMO-1001.'
    }

    return { reply, escalated }
  }

  const isStart = history.length <= 1
    || message.toLowerCase().startsWith('/start')
    || ['start interview', 'begin interview'].includes(message.toLowerCase())
  if (isStart) {
    const questions = {
      beginner: `Let's begin your ${role} interview. In 1–2 minutes, tell me about yourself and a project you've worked on.`,
      intermediate: `Welcome to your ${role} mock interview. Question 1: Describe a relevant project, the architecture you chose, and one difficult trade-off you made.`,
      advanced: `Welcome to your ${role} mock interview. Question 1: Design a production-ready system for this role. Explain architecture, scaling bottlenecks, failure modes, and trade-offs.`,
    }
    return { reply: questions[difficulty], escalated: false }
  }

  return {
    reply: `Thanks for your answer. **Feedback:** Add a specific example, your personal contribution, and a measurable result. Structure it using Situation, Task, Action, and Result (STAR).\n\n**Next question:** For the ${role} role, how would you investigate a difficult bug or unexpected production issue?`,
    escalated: false,
  }
}

export default function App() {
  const [agent, setAgent] = useState('support')
  const [sessions, setSessions] = useState(() => ({ support: newId(), interview: newId() }))
  const [messages, setMessages] = useState({support:[{role:'assistant',content:starter.support}],interview:[{role:'assistant',content:starter.interview}]})
  const [input,setInput] = useState(''), [role,setRole] = useState('Software Engineer'), [difficulty,setDifficulty] = useState('intermediate')
  const [busy,setBusy] = useState(false)
  const [escalated,setEscalated] = useState(false), [apiOnline,setApiOnline] = useState(false)
  const bottom = useRef(null)
  const sessionId = sessions[agent]
  const active = messages[agent] || []
  const isSupport = agent === 'support'
  useEffect(()=>{bottom.current?.scrollIntoView({behavior:'smooth'})},[active,busy])
  useEffect(()=>{
    if (BROWSER_DEMO) {
      setApiOnline(true)
      return
    }
    if (!API) return
    fetch(`${API}/api/health`).then(r=>r.json()).then(d=>setApiOnline(d.status==='ok')).catch(()=>setApiOnline(false))
  },[])
  function switchAgent(next){setAgent(next);setEscalated(false)}
  async function reset(){
    if (!BROWSER_DEMO) {
      try {
        const response = await fetch(`${API}/api/sessions/${sessionId}`, { method: 'DELETE' })
        if (!response.ok) throw new Error(`Session reset failed (${response.status})`)
      } catch (error) {
        console.error('Could not clear the saved session:', error)
      }
    }
    setSessions(previous => ({ ...previous, [agent]: newId() }))
    setMessages(previous => ({ ...previous, [agent]: [{ role: 'assistant', content: starter[agent] }] }))
    setEscalated(false)
    setInput('')
  }
  async function send(textOverride){
    const text=(textOverride ?? input).trim(); if(!text||busy)return
    setInput('');setMessages(p=>({...p,[agent]:[...p[agent],{role:'user',content:text}]}));setBusy(true);setEscalated(false)
    try{
      if (BROWSER_DEMO) {
        await new Promise(resolve => setTimeout(resolve, 180))
        const result = getDemoReply({ agent, message: text, role, difficulty, history: active })
        setMessages(p=>({...p,[agent]:[...p[agent],{role:'assistant',content:result.reply}]}))
        setEscalated(result.escalated)
        setApiOnline(true)
        return
      }
      const r=await fetch(`${API}/api/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,agent,message:text,role,difficulty})})
      const data=await r.json();if(!r.ok)throw new Error(data.detail||'Backend request failed')
      setMessages(p=>({...p,[agent]:[...p[agent],{role:'assistant',content:data.reply}]}));setEscalated(!!data.escalated);setApiOnline(true)
    }catch(e){setMessages(p=>({...p,[agent]:[...p[agent],{role:'assistant',content:`I couldn't reach the backend at ${API}. Start the FastAPI server and try again. Details: ${e.message}`}]}));setApiOnline(false)}
    finally{setBusy(false)}
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><Bot size={23}/></div><div><strong>Agentic AI</strong><span>LEARNING HUB</span></div></div>
      <div className="nav-label">WORKSPACE</div>
      <button className={`nav-item ${isSupport?'selected':''}`} onClick={()=>switchAgent('support')}><Headphones size={18}/><span>Customer support</span>{isSupport&&<i className="nav-dot"/>}</button>
      <button className={`nav-item ${!isSupport?'selected':''}`} onClick={()=>switchAgent('interview')}><BrainCircuit size={18}/><span>AI interview agent</span>{!isSupport&&<i className="nav-dot"/>}</button>
      <div className="sidebar-bottom"><div className="status-line"><i className={`status-dot ${apiOnline?'online':''}`}/><span>{BROWSER_DEMO?'Interactive browser demo':apiOnline?'Backend connected':'Backend disconnected'}</span></div><p>{BROWSER_DEMO?'Hosted demo · sample responses':<>Local learning environment<br/>v1.0.0 · FastAPI + React</>}</p></div>
    </aside>
    <main className="main">
      <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span> Agents <span>/</span> <b>{isSupport?'Customer Support Agent':'AI Interview Agent'}</b></div><div className="top-actions"><span className={`connection ${apiOnline?'connected':''}`}><i/> {BROWSER_DEMO?'Browser demo':apiOnline?'API connected':'API offline'}</span><div className="avatar">AI</div></div></header>
      <div className="content-grid"><section className="chat-column">
        <div className={`agent-hero ${isSupport?'violet':'blue'}`}><div className="hero-icon">{isSupport?<Headphones size={24}/>:<BrainCircuit size={24}/>}</div><div className="hero-copy"><div className="eyebrow"><Sparkles size={13}/> ACTIVE AGENT</div><h1>{isSupport?'Customer Support Agent':'AI Interview Agent'}</h1><p>{isSupport?'Helpful answers, knowledge tools, and safe escalation':'Role-based practice with feedback and follow-up questions'}</p></div><button className="icon-button hero-reset" title="Reset conversation" onClick={reset}><RotateCcw size={17}/></button></div>
        {!isSupport&&<div className="interview-settings"><label>INTERVIEW ROLE<select value={role} onChange={e=>setRole(e.target.value)}>{['Software Engineer','Frontend Developer','Backend Developer','Full Stack Developer','AI Engineer','QA Engineer','Product Manager'].map(x=><option key={x}>{x}</option>)}</select><ChevronDown size={14}/></label><label>DIFFICULTY<select value={difficulty} onChange={e=>setDifficulty(e.target.value)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select><ChevronDown size={14}/></label><button className="start-button" disabled={busy} onClick={()=>send('start interview')}><Sparkles size={15}/> Start interview</button></div>}
        <div className="chat-card"><div className="chat-heading"><div><i className="live-indicator"/><strong>Conversation</strong><small>Private local session</small></div><span className="secure"><ShieldCheck size={14}/> Safe mode</span></div>
          {escalated&&<div className="escalation-note"><ShieldCheck size={16}/><span>This conversation has been flagged for human review.</span></div>}
          <div className="messages">{active.map((m,i)=><div className={`message-row ${m.role}`} key={`${agent}-${i}`}>{m.role==='assistant'&&<div className="message-avatar"><Bot size={17}/></div>}<div className="message-bubble"><div className="message-author">{m.role==='assistant'?'Agent':'You'} <span>{m.role==='assistant'?'AI':'YOU'}</span></div><div className="message-text">{m.content}</div></div>{m.role==='user'&&<div className="user-avatar">YOU</div>}</div>)}{busy&&<div className="message-row assistant"><div className="message-avatar"><Bot size={17}/></div><div className="typing"><LoaderCircle size={15} className="spin"/> Agent is planning and reasoning…</div></div>}<div ref={bottom}/></div>
          <div className="composer-wrap"><div className="composer"><textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}} placeholder={isSupport?'Describe your issue or ask about an order…':'Type your interview answer…'} rows={1}/><button className="send-button" onClick={()=>send()} disabled={busy||!input.trim()} aria-label="Send message"><Send size={17}/></button></div><div className="composer-hint"><span>Enter to send · Shift + Enter for new line</span><span>{input.length}/6000</span></div></div>
        </div>
        <div className="quick-prompts"><span>TRY ASKING</span>{(isSupport?['Where is order DEMO-1001?','What is your refund policy?','I need a human agent']:['Start interview','How do I explain a project?','Give me a harder question']).map(p=><button key={p} onClick={()=>send(p)} disabled={busy}>{p}</button>)}</div>
      </section></div>
      <footer className="footer"><span>AGENTIC AI HUB</span><span>Built for learning · Never share passwords or payment details</span></footer>
    </main>
  </div>
}
