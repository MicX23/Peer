import { useEffect, useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import SettingsModal from './components/SettingsModal';
import SpaceModal from './components/SpaceModal';
import SpaceInfoModal from './components/SpaceInfoModal'; // Импорт
import ChatArea from './components/ChatArea';
import './style/App.css';

function App() {
  const [appState, setAppState] = useState('loading');
  const [profileName, setProfileName] = useState('User');
  
  // Модалки
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [spaceModalOpen, setSpaceModalOpen] = useState(false);
  const [spaceInfoOpen, setSpaceInfoOpen] = useState(false);
  const [selectedSpaceInfo, setSelectedSpaceInfo] = useState(null);
  
  // Чат
  const [spaces, setSpaces] = useState([]);
  const [activeSpaceId, setActiveSpaceId] = useState(null);
  const [allMessages, setAllMessages] = useState({});

  const activeSpace = spaces.find(s => s.id === activeSpaceId);
  const currentMessages = activeSpaceId ? (allMessages[activeSpaceId] || []) : [];

  const handlePyEvent = useCallback((data) => {
    console.log('[React] Event:', data);
    switch (data.type) {
      case 'node_ready': break;
      case 'need_profile_setup': setAppState('setup'); break;
      case 'user_loaded':
      case 'user_created':
        setProfileName(data.name || 'User');
        setAppState('ready');
        window.bridgeAPI?.sendCmd({ type: 'list_spaces' });
        break;
      case 'spaces_list': setSpaces(data.data || []); break;
      case 'space_created':
      case 'space_connected':
      case 'space_deleted': // Обработка удаления
        window.bridgeAPI?.sendCmd({ type: 'list_spaces' });
        break;
      case 'new_message':
        setAllMessages(prev => {
          const spaceMsgs = prev[data.space_id] || [];
          return { ...prev, [data.space_id]: [...spaceMsgs, { author: data.author, text: data.text, timestamp: Date.now(), isMe: false }] };
        });
        break;
      case 'error': console.error('[Python Error]:', data.message); break;
      default: break;
    }
  }, []);

  useEffect(() => {
    const cleanup = window.bridgeAPI?.onEvent(handlePyEvent);
    window.bridgeAPI?.sendCmd({ type: 'init' });
    return cleanup;
  }, [handlePyEvent]);

  const handleCreateProfile = (name) => window.bridgeAPI?.sendCmd({ type: 'create_user', name });

  const handleSendMessage = (spaceId, text) => {
    window.bridgeAPI?.sendCmd({ type: 'send_message', space_id: spaceId, message: text });
    setAllMessages(prev => {
      const spaceMsgs = prev[spaceId] || [];
      return { ...prev, [spaceId]: [...spaceMsgs, { author: profileName, text, timestamp: Date.now(), isMe: true }] };
    });
  };

  // Открытие информации о пространстве
  const handleOpenSpaceInfo = (space) => {
    setSelectedSpaceInfo(space);
    setSpaceInfoOpen(true);
  };

  // Удаление пространства
  const handleDeleteSpace = (spaceId) => {
    window.bridgeAPI?.sendCmd({ type: 'delete_space', id: spaceId });
    // Если удалили активное, сбрасываем выбор
    if (activeSpaceId === spaceId) setActiveSpaceId(null);
  };

  if (appState === 'loading') return <div className="loading-screen"><p>Инициализация P2P ядра...</p></div>;

  return (
    <div className="app-container">
      {appState === 'setup' && <WelcomeScreen onSubmit={handleCreateProfile} />}
      
      {appState === 'ready' && (
        <>
          <Sidebar 
            onOpenSettings={() => setSettingsOpen(true)}
            onOpenSpaceModal={() => setSpaceModalOpen(true)}
            spaces={spaces}
            activeSpaceId={activeSpaceId}
            onSelectSpace={setActiveSpaceId}
          />
          
          <ChatArea 
            activeSpace={activeSpace}
            messages={currentMessages}
            onSendMessage={handleSendMessage}
            onOpenSpaceInfo={handleOpenSpaceInfo}
            onDeleteSpace={handleDeleteSpace}
          />

          <SettingsModal 
            isOpen={settingsOpen} 
            onClose={() => setSettingsOpen(false)}
            currentName={profileName}
            onUpdateName={(name) => { setProfileName(name); setSettingsOpen(false); }}
          />

          <SpaceModal 
            isOpen={spaceModalOpen}
            onClose={() => setSpaceModalOpen(false)}
          />

          <SpaceInfoModal
            isOpen={spaceInfoOpen}
            onClose={() => setSpaceInfoOpen(false)}
            space={selectedSpaceInfo}
          />
        </>
      )}
    </div>
  );
}

export default App;