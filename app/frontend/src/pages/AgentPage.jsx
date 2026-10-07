import { DusyLogoIcon } from '../components/DusyLogo';
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import './AgentPage.css';

// Professional markdown-to-JSX renderer for agent messages
function FormatAgentText({ text }) {
  if (!text) return null;
  
  // Normalize excessive asterisks (*** or more -> **)
  let normalized = text.replace(/\*{3,}/g, '**');
  
  const lines = normalized.split('\n');
  const elements = [];
  let listItems = [];
  
  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(<ul key={`ul-${elements.length}`} className="agent-text-list">{listItems}</ul>);
      listItems = [];
    }
  };
  
  const renderInline = (str, keyPrefix) => {
    // Parse **bold** and convert to <strong>
    const parts = [];
    const regex = /\*\*(.+?)\*\*/g;
    let lastIndex = 0;
    let match;
    let partIdx = 0;
    
    while ((match = regex.exec(str)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={`${keyPrefix}-t${partIdx++}`}>{str.slice(lastIndex, match.index)}</span>);
      }
      parts.push(<strong key={`${keyPrefix}-b${partIdx++}`}>{match[1]}</strong>);
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < str.length) {
      parts.push(<span key={`${keyPrefix}-t${partIdx++}`}>{str.slice(lastIndex)}</span>);
    }
    return parts.length > 0 ? parts : str;
  };
  
  lines.forEach((line, i) => {
    const trimmed = line.trim();
    
    // Skip empty lines
    if (!trimmed) {
      flushList();
      return;
    }
    
    // Headings: ### Title or **Title:**
    if (trimmed.startsWith('### ')) {
      flushList();
      const headingText = trimmed.replace(/^###\s*/, '').replace(/\*\*/g, '');
      elements.push(<h4 key={`h-${i}`} className="agent-text-heading">{headingText}</h4>);
      return;
    }
    
    // Standalone bold line (e.g. **Patient Summary:**)
    const boldLineMatch = trimmed.match(/^\*\*([^*]+)\*\*:?$/);
    if (boldLineMatch) {
      flushList();
      elements.push(<h4 key={`bh-${i}`} className="agent-text-heading">{boldLineMatch[1]}</h4>);
      return;
    }
    
    // Bullet points: - text
    if (trimmed.startsWith('- ')) {
      const bulletContent = trimmed.slice(2);
      listItems.push(<li key={`li-${i}`}>{renderInline(bulletContent, `li-${i}`)}</li>);
      return;
    }
    
    // Checkmarks: ✓ text
    if (trimmed.startsWith('\u2713') || trimmed.startsWith('\u2714') || trimmed.startsWith('\u2705')) {
      flushList();
      elements.push(
        <div key={`check-${i}`} className="agent-text-checkmark">{renderInline(trimmed, `ck-${i}`)}</div>
      );
      return;
    }

    // Numbered list: 1. text
    if (/^\d+\.\s/.test(trimmed)) {
      flushList();
      elements.push(<div key={`num-${i}`} className="agent-text-numbered">{renderInline(trimmed, `num-${i}`)}</div>);
      return;
    }
    
    // Regular paragraph
    flushList();
    elements.push(<p key={`p-${i}`} className="agent-text-para">{renderInline(trimmed, `p-${i}`)}</p>);
  });
  
  flushList();
  return <>{elements}</>;
}

const TASK_CARDS = [
  {
    id: 'symptom_assessment',
    title: 'Symptom Assessment',
    icon: '🩺',
    desc: 'Deep multi-factor symptom triage correlating your profile, lifestyle habits, and red flags.',
    starter: "I've been experiencing recurring tension headaches lately."
  },
  {
    id: 'health_assessment',
    title: 'Health Assessment',
    icon: '📊',
    desc: 'Comprehensive check of your vitals, BMI category, and medical history.',
    starter: "Assess my overall health status based on my logged profile and metrics."
  },
  {
    id: 'lifestyle_analysis',
    title: 'Lifestyle Analysis',
    icon: '🥗',
    desc: 'Evaluate sleep schedule, stress, exercise, and hydration against clinical benchmarks.',
    starter: "Analyze how my sleep and daily stress levels might be impacting my health."
  },
  {
    id: 'risk_analysis',
    title: 'Risk Analysis',
    icon: '⚠️',
    desc: 'Proactive forecast of metabolic, cardiovascular, and chronic risks.',
    starter: "What are my highest health risk factors and what should I monitor?"
  },
  {
    id: 'health_goals',
    title: 'Health Goals',
    icon: '🎯',
    desc: 'Formulate high-leverage habit targets with actionable progress tracking.',
    starter: "Help me set realistic health goals for the next 30 days."
  }
];

export default function AgentPage() {
  const { token, user } = useAuth();
  
  // Health Context State
  const [context, setContext] = useState(null);
  const [contextLoading, setContextLoading] = useState(true);

  // Agent Interaction State
  const [selectedTask, setSelectedTask] = useState('symptom_assessment');
  const [consultationId, setConsultationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [activePipeline, setActivePipeline] = useState([]);
  const [actionSuccessMsg, setActionSuccessMsg] = useState('');

  // Action execution states
  const [executingActions, setExecutingActions] = useState({});
  const [completedActions, setCompletedActions] = useState({});
  const [recordedActionsList, setRecordedActionsList] = useState([]);

  // Past Consultations
  const [recentConsultations, setRecentConsultations] = useState([]);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Fetch user health context, actions, and recent activity on mount
  useEffect(() => {
    if (!token) {
      setContextLoading(false);
      return;
    }

    const loadInitialData = async () => {
      try {
        const [contextRes, consultsRes, actionsRes] = await Promise.all([
          api.get('/api/agent/context'),
          api.get('/api/agent/consultations'),
          api.get('/api/agent/actions').catch(() => [])
        ]);
        setContext(contextRes);
        setRecentConsultations(consultsRes || []);
        setRecordedActionsList(actionsRes || []);

        // Actions loaded into history - do not lock future messages
        // completedActions will track dynamically clicked actions per message
      } catch (err) {
        console.log('Error loading agent context:', err);
      } finally {
        setContextLoading(false);
      }
    };

    loadInitialData();
  }, [token]);

  // Start task or send message
  const handleSendMessage = async (textToSend) => {
    const text = (textToSend || inputText).trim();
    if (!text) return;

    if (!token) {
      alert('Please sign in to interact with DUSY.');
      window.location.hash = '#/login';
      return;
    }

    setInputText('');
    setActionSuccessMsg('');
    
    // Add user message to UI
    const newMsg = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, newMsg]);
    setLoading(true);

    // Dynamic thought pipeline animation
    setActivePipeline([
      { stage: 'UNDERSTAND', detail: `Parsing inquiry for ${selectedTask.replace('_', ' ')}...` },
      { stage: 'RETRIEVE', detail: 'Retrieving profile, vitals, and lifestyle telemetry...' }
    ]);

    try {
      const payload = {
        message: text,
        task_type: selectedTask,
        consultation_id: consultationId || undefined
      };

      const response = await api.post('/api/agent/interact', payload);

      if (response.consultation_id) {
        setConsultationId(response.consultation_id);
      }

      if (response.thought_pipeline && response.thought_pipeline.length > 0) {
        setActivePipeline(response.thought_pipeline);
      }

      const agentMsg = {
        role: 'agent',
        content: response.message,
        stage: response.stage || 'intake',
        quick_replies: response.quick_replies || [],
        missing_questions: response.missing_questions || [],
        red_flags: response.red_flags_detected || [],
        suggested_actions: response.suggested_actions || [],
        timestamp: new Date().toISOString()
      };

      if (response.stage === 'completed') {
        api.get('/api/agent/actions').then(res => setRecordedActionsList(res || [])).catch(() => {});
      }

      setMessages(prev => [...prev, agentMsg]);

      // Refresh recent activity list
      api.get('/api/agent/consultations').then(res => setRecentConsultations(res || []));

    } catch (err) {
      console.error('Agent interaction error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'agent',
          content: `⚠️ Encountered an error: ${err.message || 'Could not complete agentic analysis'}. Please ensure the backend is running.`,
          timestamp: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Select Task Card and seed initial starter prompt
  const handleSelectTask = (task) => {
    setSelectedTask(task.id);
    if (messages.length === 0) {
      setInputText(task.starter);
    }
  };

  // Execute offered action with live feedback
  const handleExecuteAction = async (action, actionKey) => {
    setExecutingActions(prev => ({ ...prev, [actionKey]: true }));
    setActionSuccessMsg('');

    const targetConsultationId = consultationId || (messages.length > 0 ? 'active_consultation' : 'general');

    try {
      const res = await api.post('/api/agent/action', {
        consultation_id: targetConsultationId,
        action_type: action.action_type,
        title: action.title,
        data: action.payload || {}
      });

      setCompletedActions(prev => ({
        ...prev,
        [actionKey]: true
      }));

      const successText = `✅ Recorded in Health Records: "${action.title}"!`;
      setActionSuccessMsg(successText);

      // Refresh recorded actions list
      const updatedActions = await api.get('/api/agent/actions').catch(() => []);
      setRecordedActionsList(updatedActions || []);

      setTimeout(() => setActionSuccessMsg(''), 5000);
    } catch (err) {
      alert(`Could not record action: ${err.message}`);
    } finally {
      setExecutingActions(prev => ({ ...prev, [actionKey]: false }));
    }
  };

  // Load a past consultation
  const handleLoadConsultation = async (id) => {
    try {
      setLoading(true);
      const data = await api.get(`/api/agent/consultations/${id}`);
      if (data) {
        setConsultationId(id);
        setSelectedTask(data.task_type || 'symptom_assessment');
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error('Error loading consultation:', err);
    } finally {
      setLoading(false);
    }
  };

  const startNewConsultation = () => {
    setConsultationId(null);
    setMessages([]);
    setActivePipeline([]);
    setInputText('');
  };

  return (
    <div className="agent-page-viewport">
      <div className="agent-inner-bounds">
        
        {/* ─── 1. HEADER ─── */}
        <div className="agent-header-row">
          <div>
            <div className="agent-pill-kicker">
              <span className="agent-live-spark"></span> AUTONOMOUS CLINICAL INTELLIGENCE
            </div>
            <h1 className="agent-main-title">DUSY AI Health Agent</h1>
            <p className="agent-tagline">
              Your personalized, context-aware AI health intelligence assistant.
            </p>
          </div>

          <div className="agent-header-actions">
            {consultationId && (
              <button className="btn-new-consultation" onClick={startNewConsultation}>
                + New Consultation
              </button>
            )}
          </div>
        </div>

        {/* ─── 2. HEALTH CONTEXT CARD ─── */}
        <div className="health-context-banner-card">
          <div className="context-card-left">
            <div className="context-card-badge">
              <span className="context-icon">🧬</span>
              <div>
                <h3 className="context-card-heading">Active User Health Context</h3>
                <span className="context-subtext">
                  Connected to authenticated profile: <strong>{context?.user_name || user?.name || 'User'}</strong>
                </span>
              </div>
            </div>

            {/* Checklist of available telemetry */}
            <div className="context-telemetry-chips">
              <span className={`telemetry-chip ${context?.has_profile ? 'active' : 'inactive'}`}>
                {context?.has_profile ? '✓' : '○'} Health Profile
              </span>
              <span className={`telemetry-chip ${context?.has_medical_conditions ? 'active' : 'inactive'}`}>
                {context?.has_medical_conditions ? '✓' : '○'} Medical History
              </span>
              <span className={`telemetry-chip ${context?.has_medications ? 'active' : 'inactive'}`}>
                {context?.has_medications ? '✓' : '○'} Current Medications
              </span>
              <span className={`telemetry-chip ${context?.has_lifestyle ? 'active' : 'inactive'}`}>
                {context?.has_lifestyle ? '✓' : '○'} Lifestyle Data
              </span>
              <span className={`telemetry-chip ${context?.has_history ? 'active' : 'inactive'}`}>
                {context?.has_history ? '✓' : '○'} Health History
              </span>
            </div>
          </div>

          <div className="context-card-right">
            <div className="context-score-display">
              <div className="context-score-circle">
                <span className="context-percentage">{context?.completion_percentage || 50}%</span>
                <span className="context-percentage-label">Context</span>
              </div>
              <a href="#/profile" className="btn-update-context">
                Update Profile &rarr;
              </a>
            </div>
          </div>
        </div>

        {/* ─── 3. AGENT TASK CARDS ─── */}
        <div className="agent-tasks-section">
          <div className="section-label-bar">Select Agent Investigation Task:</div>
          <div className="tasks-grid-row">
            {TASK_CARDS.map((task) => (
              <div
                key={task.id}
                className={`task-select-card ${selectedTask === task.id ? 'selected' : ''}`}
                onClick={() => handleSelectTask(task)}
              >
                <div className="task-card-icon">{task.icon}</div>
                <h4 className="task-card-title">{task.title}</h4>
                <p className="task-card-desc">{task.desc}</p>
                {selectedTask === task.id && <span className="task-active-indicator">&bull; Active Task</span>}
              </div>
            ))}
          </div>
        </div>

        {/* ─── 4. AGENT WORKSPACE ─── */}
        <div className="agent-workspace-container">
          {/* Workspace Clean Header Bar */}
          <div className="workspace-header-bar">
            <div className="workspace-header-status">
              <span className="live-spark-dot"></span>
              <span className="workspace-header-title">DUSY Health Agent</span>
            </div>
            {messages.length > 0 && (
              <button className="btn-clean-reset" onClick={startNewConsultation} title="Start new assessment">
                + New Consultation
              </button>
            )}
          </div>
          {actionSuccessMsg && (
            <div className="floating-action-toast">
              <span>{actionSuccessMsg}</span>
              <button className="toast-dismiss-btn" onClick={() => setActionSuccessMsg('')}>✕</button>
            </div>
          )}

          {/* Messages Area */}
          <div className="agent-messages-scroll-box">
            {messages.length === 0 && (
              <div className="workspace-empty-state">
                <div className="empty-icon">🤖</div>
                <h3>Personalized DUSY Agent Ready</h3>
                <p>
                  I have pre-loaded your profile metrics. Tell me what you are experiencing,
                  or choose a task above to begin an interactive diagnostic consultation.
                </p>
                <div className="empty-starter-chips">
                  <button onClick={() => handleSendMessage("I've been having frequent headaches for the past 2 weeks.")}>
                    👉 "I've been having frequent headaches for 2 weeks"
                  </button>
                  <button onClick={() => handleSendMessage("Evaluate my current lifestyle and daily habits.")}>
                    👉 "Evaluate my lifestyle habits"
                  </button>
                </div>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={`agent-bubble-row ${msg.role === 'user' ? 'user-turn' : 'agent-turn'}`}>
                {msg.role === 'agent' && <div className="agent-avatar-cube"><DusyLogoIcon size={18} /></div>}
                
                <div className={`agent-msg-box ${msg.role === 'user' ? 'box-user' : 'box-agent'}`}>
                  
                  {/* Message body */}
                  <div className="agent-formatted-text"><FormatAgentText text={msg.content} /></div>

                  {/* Red Flags Alert if detected */}
                  {msg.red_flags && msg.red_flags.length > 0 && (
                    <div className="agent-red-flag-alert">
                      <div className="rf-alert-title">🚨 Safety Screen Alert:</div>
                      <ul>
                        {msg.red_flags.map((rf, rIdx) => (
                          <li key={rIdx}>{rf}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Missing Questions (Interactive click-to-answer) */}
                  {msg.missing_questions && msg.missing_questions.length > 0 && (
                    <div className="agent-probing-box">
                      <div className="probing-header">❓ Information Needed for Precise Evaluation:</div>
                      <div className="probing-questions-list">
                        {msg.missing_questions.map((q, qIdx) => (
                          <div
                            key={qIdx}
                            className="probing-question-chip"
                            onClick={() => setInputText(`Regarding "${q}": `)}
                          >
                            <span>{q}</span>
                            <span className="chip-reply-action">Click to answer &rarr;</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Quick Reply Choice Chips */}
                  {msg.quick_replies && msg.quick_replies.length > 0 && (
                    <div className="agent-quick-replies">
                      {msg.quick_replies.map((chip, cIdx) => (
                        <button
                          key={cIdx}
                          type="button"
                          className="agent-choice-chip"
                          onClick={() => handleSendMessage(chip)}
                          disabled={loading}
                        >
                          {chip}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Interactive Action Offers */}
                  {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                    <div className="agent-actions-shelf">
                      <div className="actions-shelf-title">⚡ Available Agent Actions:</div>
                      <div className="action-cards-grid">
                        {msg.suggested_actions.map((act, aIdx) => {
                          const actionKey = `msg_${idx}_act_${aIdx}_${act.title}`;
                          const isExecuting = executingActions[actionKey];
                          const isCompleted = completedActions[actionKey];

                          return (
                            <div key={aIdx} className={`offered-action-card ${isCompleted ? 'card-action-done' : ''}`}>
                              <div className="action-card-header">
                                <span className="action-type-pill">{act.action_type.replace('_', ' ').toUpperCase()}</span>
                                <button
                                  className={`btn-take-action ${isCompleted ? 'btn-action-completed' : ''} ${isExecuting ? 'btn-action-saving' : ''}`}
                                  onClick={() => handleExecuteAction(act, actionKey)}
                                  disabled={isExecuting || isCompleted}
                                >
                                  {isExecuting ? '⏳ Saving...' : isCompleted ? '✓ Saved' : 'Execute →'}
                                </button>
                              </div>
                              <h5 className="action-card-title">{act.title}</h5>
                              {act.description && <p className="action-card-desc">{act.description}</p>}
                              
                              {isCompleted && (
                                <div className="action-success-badge-inline">
                                  ✅ Recorded in your Health Records &amp; Goal Database
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            ))}

            {loading && (
              <div className="agent-bubble-row agent-turn">
                <div className="agent-avatar-cube"><DusyLogoIcon size={18} /></div>
                <div className="agent-msg-box box-agent box-analyzing">
                  <span className="analyzing-spinner"></span>
                  <span>Agent is querying context, evaluating clinical guidelines, and reasoning...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="agent-input-dock">
            <input
              type="text"
              className="agent-text-field"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder={`Describe your concern or answer missing questions for ${selectedTask.replace('_', ' ')}...`}
              disabled={loading}
            />
            <button
              className="btn-agent-send"
              onClick={() => handleSendMessage()}
              disabled={loading || !inputText.trim()}
            >
              Consult Agent &rarr;
            </button>
          </div>
        </div>

        {/* ─── 5. RECENT AGENT ACTIVITY ─── */}
        <div className="recent-activity-section">
          <h3 className="recent-title">Recent Agent Activity &amp; Consultations</h3>
          
          {recentConsultations.length === 0 ? (
            <div className="no-activity-placeholder">
              No previous consultations recorded yet. Start your first assessment above to establish your longitudinal health record!
            </div>
          ) : (
            <div className="recent-consults-grid">
              {recentConsultations.map((item) => (
                <div
                  key={item.id}
                  className={`past-consult-item ${consultationId === item.id ? 'current-active' : ''}`}
                  onClick={() => handleLoadConsultation(item.id)}
                >
                  <div className="past-consult-top">
                    <span className="past-task-tag">{item.task_type.replace('_', ' ').toUpperCase()}</span>
                    <span className="past-date">{new Date(item.updated_at).toLocaleDateString()}</span>
                  </div>
                  <h4 className="past-consult-title">{item.title}</h4>
                  <p className="past-consult-preview">{item.preview}</p>
                  <div className="past-consult-footer">
                    <span>💬 {item.message_count} messages</span>
                    <span className="open-past-link">Re-open &rarr;</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ─── 6. RECORDED HEALTH LOGS & ACTIVE GOALS ─── */}
        <div className="recorded-actions-section">
          <div className="actions-section-header">
            <h3 className="recent-title">📋 Recorded Health Logs &amp; Active Goals</h3>
            <span className="actions-count-pill">{recordedActionsList.length} Items Recorded</span>
          </div>

          {recordedActionsList.length === 0 ? (
            <div className="no-activity-placeholder">
              No actions recorded yet. When the Agent offers actions, click "Execute →" to save them here!
            </div>
          ) : (
            <div className="recorded-actions-grid">
              {recordedActionsList.map((item) => (
                <div key={item.id || item._id} className="recorded-action-card">
                  <div className="rec-top-row">
                    <span className="rec-type-badge">{item.action_type?.replace('_', ' ').toUpperCase()}</span>
                    <span className="rec-date">{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  <h4 className="rec-title">{item.title}</h4>
                  {item.data && Object.keys(item.data).length > 0 && (
                    <div className="rec-data-box">
                      {Object.entries(item.data).map(([k, v]) => (
                        <div key={k} className="rec-data-row">
                          <strong>{k}:</strong> <span>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  <span className="rec-status-tag">✓ Completed / Active</span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
