import React from 'react';
import { X } from 'lucide-react';
import '../style/ChatArea.css'; // Используем те же стили или создай SpaceInfoModal.css

export default function SpaceInfoModal({ isOpen, onClose, space }) {
  if (!isOpen || !space) return null;

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="space-info-modal" onClick={(e) => e.stopPropagation()}>
        <div className="space-info-header">
          <h3 className="settings-title">Информация о пространстве</h3>
          <button onClick={onClose} className="settings-close-btn">
            <X size={24} />
          </button>
        </div>
        <div className="space-info-body">
          <div className="info-row">
            <div className="info-label">Название</div>
            <div className="info-value" style={{ fontFamily: 'inherit' }}>{space.name}</div>
          </div>
          <div className="info-row">
            <div className="info-label">ID Пространства (Share this)</div>
            <div className="info-value">{space.id}</div>
          </div>
          <div className="info-row">
            <div className="info-label">Адрес (Addr)</div>
            <div className="info-value">{space.addr || 'N/A'}</div>
          </div>
        </div>
      </div>
    </div>
  );
}