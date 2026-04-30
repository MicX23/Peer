import React, { useState, useRef, useEffect } from 'react';
import { MoreVertical, Info, Trash2, Paperclip, Send, FileText, X, Download, FolderOpen } from 'lucide-react';
import '../style/ChatArea.css';

// Проверка наличия Electron API
const isElectron = window.electronAPI !== undefined;

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default function ChatArea({ activeSpace, messages, onSendMessage, onOpenSpaceInfo, onDeleteSpace }) {
  const [inputValue, setInputValue] = useState('');
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null); // { name, size, type, raw }
  const [fileTag, setFileTag] = useState(''); // Метка файла
  
  // Состояние для контекстного меню файла
  const [contextMenu, setContextMenu] = useState(null); // { x, y, msg }
  
  const messagesEndRef = useRef(null);
  const menuRef = useRef(null);
  const fileInputRef = useRef(null);

  // Автопрокрутка вниз при новых сообщениях
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Закрытие выпадающего меню хедера при клике вне его
  useEffect(() => {
    function handleClickOutside(event) {
      // 1. Логика для меню хедера (остается без изменений)
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsMenuOpen(false);
      }

      // 2. Логика для контекстного меню файлов
      // Проверяем, существует ли меню сейчас
      if (contextMenu) {
        // Ищем элемент меню в DOM. 
        // Примечание: так как меню рендерится условно, лучше дать ему ref или класс.
        // Здесь мы используем класс .file-context-menu, который у вас уже есть.
        const contextMenuElement = document.querySelector('.file-context-menu');
        
        // Если клик был НЕ по самому меню, закрываем его
        if (contextMenuElement && !contextMenuElement.contains(event.target)) {
          setContextMenu(null);
        }
      }
    }

    // Используем mousedown, чтобы перехватывать клик до того, как он завершится
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [contextMenu]); // Зависимость от contextMenu важна, чтобы видеть актуальное состояние

  // --- Обработчики Drag & Drop ---

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.size > 50 * 1024 * 1024) { // Лимит 50MB
        alert("Файл слишком большой (макс 50MB)");
        return;
      }
      setAttachedFile({
        name: file.name,
        size: file.size,
        type: file.type,
        raw: file
      });
      setTimeout(() => document.getElementById('file-tag-input')?.focus(), 100);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile({
        name: file.name,
        size: file.size,
        type: file.type,
        raw: file
      });
      setTimeout(() => document.getElementById('file-tag-input')?.focus(), 100);
    }
  };

  // --- Отправка сообщений ---

  const handleSend = () => {
    if ((!inputValue.trim() && !attachedFile) || !activeSpace) return;

    // Отправляем текст и/или файл
    onSendMessage(activeSpace.id, inputValue.trim(), attachedFile, fileTag);
    
    setInputValue('');
    setAttachedFile(null);
    setFileTag('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // --- Контекстное меню файлов (Electron) ---

  const handleFileContextMenu = (e, msg) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      msg: msg
    });
  };

  const handleOpenFile = async (msg) => {
    console.log(">>> КЛИК ПО 'ОТКРЫТЬ ФАЙЛ'");
    console.log("Данные сообщения:", msg);

    if (!msg.filePath) {
      console.error("Ошибка: Нет пути к файлу в сообщении");
      alert("Путь к файлу не указан.");
      return;
    }

    // Проверка наличия API
    if (window.electronAPI) {
      console.log("electronAPI найден:", window.electronAPI);
      
      if (typeof window.electronAPI.openFile === 'function') {
        console.log("Вызываю openFile с путем:", msg.filePath);
        try {
          const result = await window.electronAPI.openFile(msg.filePath);
          console.log("Ответ от openFile:", result);
        } catch (err) {
          console.error("Исключение при вызове openFile:", err);
          alert(`Ошибка: ${err.message}`);
        }
      } else {
        console.error("Метод openFile НЕ НАЙДЕН в electronAPI");
        alert("Ошибка: Метод openFile не доступен в API.");
      }
    } else {
      console.error("window.electronAPI НЕ СУЩЕСТВУЕТ");
      alert("Electron API не подключено. Запустите приложение через Electron.");
    }
    
    setContextMenu(null);
  };

  const handleShowInFolder = async (msg) => {
    console.log(">>> КЛИК ПО 'ПОКАЗАТЬ В ПАПКЕ'");
    
    if (!msg.filePath) {
      alert("Путь к файлу не указан.");
      return;
    }

    if (window.electronAPI && typeof window.electronAPI.showItemInFolder === 'function') {
      console.log("Вызываю showItemInFolder...");
      try {
        await window.electronAPI.showItemInFolder(msg.filePath);
      } catch (err) {
        console.error("Ошибка showItemInFolder:", err);
        alert(`Ошибка: ${err.message}`);
      }
    } else {
      console.warn("API недоступно, копирую путь...");
      navigator.clipboard.writeText(msg.filePath);
      alert(`API недоступно. Путь скопирован: ${msg.filePath}`);
    }
    setContextMenu(null);
  };

  // --- Рендер ---

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
    <div 
      className="chat-area"
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      {/* Хедер чата */}
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-header-hash">#</span>
          {activeSpace.name}
        </div>
        
        <div className="chat-header-actions" ref={menuRef}>
          <button className="header-menu-btn" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            <MoreVertical size={20} />
          </button>

          {isMenuOpen && (
            <div className="header-dropdown">
              <button className="dropdown-item" onClick={() => { onOpenSpaceInfo(activeSpace); setIsMenuOpen(false); }}>
                <Info size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} /> Информация
              </button>
              <button className="dropdown-item danger" onClick={() => {
                if (window.confirm(`Удалить "${activeSpace.name}"?`)) onDeleteSpace(activeSpace.id);
                setIsMenuOpen(false);
              }}>
                <Trash2 size={16} style={{ marginRight: 8, verticalAlign: 'middle' }} /> Удалить
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
            // Системное сообщение
            if (msg.isSystem) {
              return (
                <div key={`sys-${index}`} className="system-message">
                  <span className="system-text">{msg.text}</span>
                </div>
              );
            }

            // Сообщение с файлом
            if (msg.fileName) {
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
                
                {/* Блок с файлом + Правый клик */}
                <div 
                  className={`message-bubble file-bubble ${isMe ? 'bubble-me' : 'bubble-them'}`}
                  onContextMenu={(e) => handleFileContextMenu(e, msg)}
                >
                  {msg.text && <div className="message-content">{msg.text}</div>}
                  
                  <div className="file-attachment">
                    <FileText size={20} className="file-icon" />
                    <div className="file-info">
                      <span className="file-name">{msg.fileName}</span>
                      <span className="file-size">{formatFileSize(msg.fileSize)}</span>
                      {msg.tag && <span className="file-tag">#{msg.tag}</span>}
                    </div>
                  </div>
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
            }

            // Обычное текстовое сообщение
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

      {/* Область ввода */}
      <div className="chat-input-container">
        {/* Панель прикрепленного файла */}
        {attachedFile && (
          <div className="pending-file-panel">
            <div className="pending-file-info">
              <FileText size={16} />
              <span>{attachedFile.name} ({formatFileSize(attachedFile.size)})</span>
            </div>
            <div className="pending-file-controls">
              <input 
                id="file-tag-input"
                type="text" 
                placeholder="#метка (опционально)" 
                value={fileTag}
                onChange={(e) => setFileTag(e.target.value.replace('#', ''))}
                className="file-tag-input"
              />
              <X size={16} className="pending-file-remove" onClick={() => {
                setAttachedFile(null);
                setFileTag('');
                if (fileInputRef.current) fileInputRef.current.value = '';
              }} />
            </div>
          </div>
        )}

        <div className={`chat-input-wrapper ${dragActive ? 'drag-over' : ''}`}>
          <input 
            type="file" 
            ref={fileInputRef} 
            style={{ display: 'none' }} 
            onChange={handleFileSelect} 
          />
          
          <button className="attach-btn" onClick={() => fileInputRef.current?.click()} title="Прикрепить файл">
            <Paperclip size={20} />
          </button>

          <input
            type="text"
            className="chat-input"
            placeholder={attachedFile ? "Добавьте комментарий..." : `Написать в #${activeSpace.name}`}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!activeSpace}
          />

          <button 
            className="send-btn"
            onClick={handleSend}
            disabled={!inputValue.trim() && !attachedFile}
            title="Отправить"
          >
            <Send size={20} />
          </button>
        </div>
      </div>

      {/* Контекстное меню для файлов (Electron) */}
      {contextMenu && (
        <>
          {/* Затемнение фона для закрытия по клику вне меню */}
          <div 
            style={{
              position: 'fixed',
              top: 0, left: 0, right: 0, bottom: 0,
              zIndex: 999
            }}
            onClick={() => setContextMenu(null)}
          />
          
          {/* Само меню */}
          <div 
            className="file-context-menu"
            style={{
              left: contextMenu.x,
              top: contextMenu.y,
            }}
          >
            <button 
              className="context-menu-item"
              onClick={() => handleOpenFile(contextMenu.msg)}
            >
              <Download size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Открыть файл
            </button>
            
            <button 
              className="context-menu-item"
              onClick={() => handleShowInFolder(contextMenu.msg)}
            >
              <FolderOpen size={14} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Показать в папке
            </button>
          </div>
        </>
      )}
    </div>
  );
}