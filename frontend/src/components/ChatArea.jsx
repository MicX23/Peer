import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, Info, Trash2 } from 'lucide-react'; // Импортируем иконки
import '../style/ChatArea.css';

export default function ChatArea({ activeSpace, messages, onSendMessage, onOpenSpaceInfo, onDeleteSpace }) {
  const [inputValue, setInputValue] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);

  // Автоскролл
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Закрытие меню при клике вне его
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (inputValue.trim() && activeSpace) {
        onSendMessage(activeSpace.id, inputValue.trim());
        setInputValue('');
      }
    }
  };

  if (!activeSpace) {
    return (
      <div className="chat-area">
        <div className="chat-empty-state">
          <div className="chat-empty-title">Добро пожаловать!</div>
          <p>Выберите или создайте пространство слева.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-area">
      {/* Заголовок чата */}
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-header-hash">#</span>
          {activeSpace.name}
        </div>
        
        {/* Меню действий */}
        <div className="chat-header-actions" ref={menuRef}>
          <button 
            className="header-menu-btn"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <MoreVertical size={20} />
          </button>

          {isMenuOpen && (
            <div className="header-dropdown">
              <button 
                className="dropdown-item"
                onClick={() => {
                  onOpenSpaceInfo(activeSpace);
                  setIsMenuOpen(false);
                }}
              >
                <Info size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
                Информация
              </button>
              <button 
                className="dropdown-item danger"
                onClick={() => {
                  if (window.confirm(`Удалить пространство "${activeSpace.name}"?`)) {
                    onDeleteSpace(activeSpace.id);
                  }
                  setIsMenuOpen(false);
                }}
              >
                <Trash2 size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} />
                Удалить
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Список сообщений */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="chat-empty-state" style={{ justifyContent: 'flex-start', paddingTop: 40 }}>
            <p>Это начало истории канала <strong>{activeSpace.name}</strong>.</p>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isMe = msg.isMe;
            return (
              <div key={index} className={`message-group ${isMe ? 'message-group-me' : ''}`}>
                {!isMe && (
                  <div className="message-header">
                    <span className="message-author">{msg.author || 'Unknown'}</span>
                    <span className="message-timestamp">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
                
                <div className={`message-bubble ${isMe ? 'bubble-me' : 'bubble-them'}`}>
                  <div className="message-content">{msg.text}</div>
                </div>
                
                {isMe && (
                  <div className="message-header" style={{ justifyContent: 'flex-end' }}>
                    <span className="message-timestamp">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                )}
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Поле ввода */}
      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <input
            type="text"
            className="chat-input"
            placeholder={`Написать в #${activeSpace.name}`}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!activeSpace}
          />
        </div>
      </div>
    </div>
  );
}