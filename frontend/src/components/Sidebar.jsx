import React from 'react';
import { MessageSquare, Users, Plus, User, Settings } from 'lucide-react';
import '../style/Sidebar.css';

export default function Sidebar({ onOpenSettings, spaces, activeSpaceId, onSelectSpace, onOpenSpaceModal }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        <button className="sidebar-icon active">
          <MessageSquare size={20} />
        </button>
        
        <div className="sidebar-divider" />
        
        {spaces.map(space => (
          <button
            key={space.id}
            onClick={() => onSelectSpace(space.id)}
            className={`sidebar-icon ${activeSpaceId === space.id ? 'active' : ''}`}
            title={space.name}
          >
            <span style={{ fontSize: 14, fontWeight: 'bold' }}>
              {space.name.charAt(0).toUpperCase()}
            </span>
          </button>
        ))}

        {/* Кнопка добавления/подключения */}
        <button 
          className="sidebar-icon add"
          onClick={onOpenSpaceModal}
        >
          <Plus size={20} />
        </button>
      </div>

      <div className="sidebar-bottom">
        <button className="sidebar-profile-btn">
          <User size={20} />
        </button>
        <button onClick={onOpenSettings} className="sidebar-settings-btn">
          <Settings size={20} />
        </button>
      </div>
    </aside>
  );
}