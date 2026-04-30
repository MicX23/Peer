import React, { useState } from 'react';
import '../style/SpaceModal.css';

export default function SpaceModal({ isOpen, onClose }) {
  const [mode, setMode] = useState('create'); // 'create' or 'connect'
  const [name, setName] = useState('');
  const [spaceId, setSpaceId] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (mode === 'create') {
      if (!name.trim()) return;
      window.bridgeAPI?.sendCmd({ type: 'create_space', name: name.trim() });
    } else {
      if (!spaceId.trim()) return;
      window.bridgeAPI?.sendCmd({ type: 'connect_space', id: spaceId.trim() });
    }
    
    onClose();
    // Сброс полей
    setName('');
    setSpaceId('');
  };

  return (
    <div className="space-modal-overlay" onClick={onClose}>
      <div className="space-modal" onClick={(e) => e.stopPropagation()}>
        <div className="space-modal-header">
          <h2 className="space-modal-title">Пространства</h2>
        </div>
        
        <div className="space-modal-tabs">
          <button 
            className={`space-tab ${mode === 'create' ? 'active' : ''}`}
            onClick={() => setMode('create')}
          >
            Создать
          </button>
          <button 
            className={`space-tab ${mode === 'connect' ? 'active' : ''}`}
            onClick={() => setMode('connect')}
          >
            Подключиться
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-modal-body">
          {mode === 'create' ? (
            <div className="space-input-group">
              <label className="space-label">Название пространства</label>
              <input 
                type="text" 
                className="space-input" 
                placeholder="Мой чат" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
          ) : (
            <div className="space-input-group">
              <label className="space-label">ID пространства</label>
              <input 
                type="text" 
                className="space-input" 
                placeholder="Введите ID..." 
                value={spaceId}
                onChange={(e) => setSpaceId(e.target.value)}
                autoFocus
              />
            </div>
          )}

          <div className="space-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Отмена
            </button>
            <button 
              type="submit" 
              className="btn-primary"
              disabled={mode === 'create' ? !name.trim() : !spaceId.trim()}
            >
              {mode === 'create' ? 'Создать' : 'Подключиться'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}