import { DusyLogoIcon } from '../components/DusyLogo';
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api/axios';
import './ChatPage.css';

export default function ChatPage() {
  const { token, user } = useAuth();
  const [messages, setMessages] = useState([
    {
      role: 'ai',
      content: 'Hello! I am your AI Health Assistant powered by Gemini. How are you feeling today? You can ask me about symptoms, lifestyle improvements, vitals, or general wellness advice.'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

  const quickPrompts = [
    "I have had a mild headache and fever for 2 days",
    "What are the best habits to reduce metabolic risk?",
    "How does 6 hours of sleep affect heart health?"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (messageToSend) => {
    const text = (typeof messageToSend === 'string' ? messageToSend : input).trim();
    if (!text) return;

    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);

    try {
      const payload = { message: text };
      if (conversationId) {
        payload.conversation_id = conversationId;
      }

      const response = await api.post('/api/chat/message', payload);
      
      const aiReply = response?.message || response?.reply || response?.data?.message || 'I have analyzed your query. Please consult a doctor for definitive medical evaluation.';
      
      if (response?.conversation_id) {
        setConversationId(response.conversation_id);
      }

      setMessages(prev => [...prev, { role: 'ai', content: aiReply }]);
    } catch (error) {
      console.error('Chat error:', error);
      let errorMsg = 'Sorry, I had trouble processing that. ';
      if (!token) {
        errorMsg += 'Please sign in first so I can access your health context and securely save our chat!';
      } else {
        errorMsg += (error.message || 'Please check if the backend server is running.');
      }
      setMessages(prev => [...prev, { role: 'ai', content: errorMsg }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-viewport-page">
      <div className="chat-frame-box">
        
        {/* Chat Top Header */}
        <div className="chat-header-bar">
          <div className="chat-header-left">
            <div className="chat-avatar-bubble">AI</div>
            <div>
              <h3 className="chat-header-title">DUSY AI Chat</h3>
              <span className="chat-online-indicator">
                <span className="online-green-dot"></span> Powered by Gemini 3.6 Flash
              </span>
            </div>
          </div>
          <div className="chat-header-right">
            {token ? (
              <span className="chat-user-tag">👤 {user?.name || 'Logged In'}</span>
            ) : (
              <a href="#/login" className="chat-login-prompt-btn">Sign in for personalized context</a>
            )}
          </div>
        </div>

        {/* Suggested Quick Questions */}
        <div className="chat-quick-chips">
          <span className="chips-title">Suggested:</span>
          {quickPrompts.map((prompt, idx) => (
            <button
              key={idx}
              className="quick-chip-btn"
              onClick={() => handleSend(prompt)}
              disabled={loading}
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Chat Messages Log */}
        <div className="chat-messages-area">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-bubble-row ${msg.role === 'user' ? 'row-user' : 'row-ai'}`}>
              {msg.role === 'ai' && <div className="chat-msg-avatar"><DusyLogoIcon size={16} /></div>}
              <div className={`chat-bubble ${msg.role === 'user' ? 'bubble-user' : 'bubble-ai'}`}>
                {msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-bubble-row row-ai">
              <div className="chat-msg-avatar"><DusyLogoIcon size={16} /></div>
              <div className="chat-bubble bubble-ai bubble-typing">
                <span className="dot-pulse"></span>
                <span className="dot-pulse"></span>
                <span className="dot-pulse"></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Chat Bottom Input */}
        <div className="chat-input-area">
          <input
            type="text"
            className="chat-text-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about symptoms, diet, vitals, or health risks..."
            disabled={loading}
          />
          <button
            className="chat-submit-btn"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            Send &rarr;
          </button>
        </div>

        <div className="chat-disclaimer-bar">
          ⚠️ AI health information is for guidance and prevention, not medical diagnosis.
        </div>

      </div>
    </div>
  );
}
