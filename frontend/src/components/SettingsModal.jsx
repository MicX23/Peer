import { useState, useEffect } from 'react';
import { X, User, Shield, Bell, Settings as SettingsIcon } from 'lucide-react';
import '../style/SettingsModal.css';

const tabs = [
  { id: 'profile', label: 'Профиль', icon: User },
  { id: 'security', label: 'Безопасность', icon: Shield },
  { id: 'notifications', label: 'Уведомления', icon: Bell },
  { id: 'appearance', label: 'Внешний вид', icon: SettingsIcon },
];

export default function SettingsModal({ isOpen, onClose, currentName, onUpdateName }) {
  const [activeTab, setActiveTab] = useState('profile');
  const [nameInput, setNameInput] = useState(currentName);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (isOpen) {
      setNameInput(currentName);
      setStatus('');
      setIsSaving(false);
    }
  }, [isOpen, currentName]);

  useEffect(() => {
    if (isSaving && nameInput === currentName) {
      setIsSaving(false);
      setStatus('Сохранено');
      setTimeout(() => setStatus(''), 2000);
    }
  }, [currentName, isSaving, nameInput]);

  const handleSave = () => {
    const newName = nameInput.trim();
    if (!newName || newName === currentName) return;
    
    setIsSaving(true);
    setStatus('Сохранение...');
    onUpdateName(newName);
  };

  if (!isOpen) return null;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-container" onClick={(e) => e.stopPropagation()}>
        <div className="settings-content">
          <div className="settings-header">
            <h2 className="settings-title">
              {tabs.find(t => t.id === activeTab)?.label || 'Настройки'}
            </h2>
            <button onClick={onClose} className="settings-close-btn">
              <X size={24} />
            </button>
          </div>
          
          <div className="settings-body">
            {activeTab === 'profile' && (
              <div className="settings-section">
                <label className="settings-label">Имя пользователя</label>
                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  className="settings-input"
                  maxLength={32}
                  autoFocus
                />
                <div className="settings-actions">
                  <button
                    onClick={handleSave}
                    disabled={isSaving || !nameInput.trim() || nameInput.trim() === currentName}
                    className="settings-save-btn"
                  >
                    {isSaving ? 'Сохранение...' : 'Сохранить'}
                  </button>
                  {status && <span className="settings-status">{status}</span>}
                </div>
              </div>
            )}
            {activeTab !== 'profile' && (
              <div className="settings-placeholder">
                Раздел "{tabs.find(t => t.id === activeTab)?.label}" в разработке
              </div>
            )}
          </div>
        </div>

        <div className="settings-nav">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`settings-nav-item ${activeTab === tab.id ? 'active' : ''}`}
            >
              <tab.icon size={20} />
              {tab.label}
            </button>
          ))}
          <div className="settings-nav-footer">
            <button onClick={onClose} className="settings-nav-close">
              <X size={20} />
              Закрыть
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}