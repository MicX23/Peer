import { useEffect, useState, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import WelcomeScreen from './components/WelcomeScreen';
import SettingsModal from './components/SettingsModal';
import SpaceModal from './components/SpaceModal';
import SpaceInfoModal from './components/SpaceInfoModal';
import ChatArea from './components/ChatArea'; // Ваш новый компонент
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
  const [pendingConnectSpaceId, setPendingConnectSpaceId] = useState(null);

  // --- Обработчик событий от Python ---
  const handlePyEvent = useCallback((data) => {
    console.log('[React] Event:', data);
    
    switch (data.type) {
      case 'node_ready': 
        break;
        
      case 'need_profile_setup': 
        setAppState('setup'); 
        break;
        
      case 'user_loaded':
      case 'user_created':
        setProfileName(data.name || 'User');
        setAppState('ready');
        // Запрашиваем список пространств при загрузке
        window.bridgeAPI?.sendCmd({ type: 'list_spaces' });
        break;
        
      case 'spaces_list':
        const newSpaces = data.data || [];
        setSpaces(newSpaces);

        // Если мы ждали подключения к конкретному пространству, активируем его
        if (pendingConnectSpaceId && newSpaces.some(s => s.id === pendingConnectSpaceId)) {
            setActiveSpaceId(pendingConnectSpaceId);
            setPendingConnectSpaceId(null);
        }
        break;

      case 'space_created':
      case 'space_deleted':
        window.bridgeAPI?.sendCmd({ type: 'list_spaces' });
        break;

      case 'space_connected':
        // Python сообщил, что подключение успешно. Ждем обновления списка.
        setPendingConnectSpaceId(data.id);
        window.bridgeAPI?.sendCmd({ type: 'list_spaces' });
        break;

      // --- Текстовые сообщения ---
      case 'new_message':
        setAllMessages(prev => {
          const spaceMsgs = prev[data.space_id] || [];
          return {
            ...prev,
            [data.space_id]: [...spaceMsgs, {
              author: data.author,
              text: data.text,
              timestamp: Date.now(),
              isMe: data.isMe || false
            }]
          };
        });
        break;

      // --- Файловые сообщения ---
      case 'new_file_message':
        setAllMessages(prev => {
          const spaceMsgs = prev[data.space_id] || [];
          return {
            ...prev,
            [data.space_id]: [...spaceMsgs, {
              author: data.author,
              fileName: data.fileName,
              fileSize: data.fileSize,
              filePath: data.filePath, // Путь для открытия в Electron
              tag: data.tag,
              timestamp: Date.now(),
              isMe: data.isMe || false
            }]
          };
        });
        break;

      // --- Системные события (вход/выход/ошибки) ---
      case 'system_event':
        if (data.isSystem) {
            setAllMessages(prev => {
            const spaceMsgs = prev[data.space_id] || [];
            return {
                ...prev,
                [data.space_id]: [...spaceMsgs, {
                type: 'system',
                text: data.text,
                timestamp: Date.now(),
                isSystem: true
                }]
            };
            });
        }
        break;

      case 'error': 
        console.error('[Python Error]:', data.message); 
        break;
        
      default: 
        break;
    }
  }, [pendingConnectSpaceId]);

  // --- Инициализация моста ---
  useEffect(() => {
    const cleanup = window.bridgeAPI?.onEvent(handlePyEvent);
    window.bridgeAPI?.sendCmd({ type: 'init' });
    return cleanup;
  }, [handlePyEvent]);

  // --- Действия пользователя ---

  const handleCreateProfile = (name) => {
    window.bridgeAPI?.sendCmd({ type: 'create_user', name });
  };

  const handleSendMessage = (spaceId, text, file = null, tag = '') => {
    // 1. Отправка текста
    if (text) {
      // Оптимистичное обновление UI (показываем сообщение сразу)
      setAllMessages(prev => {
        const spaceMsgs = prev[spaceId] || [];
        return {
          ...prev,
          [spaceId]: [...spaceMsgs, {
            author: profileName,
            text: text,
            timestamp: Date.now(),
            isMe: true
          }]
        };
      });

      window.bridgeAPI?.sendCmd({
        type: 'send_message',
        space_id: spaceId,
        message: text
      });
    }

    // 2. Отправка файла
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        const base64Data = reader.result.split(',')[1];
        
        // Отправляем команду в Python
        window.bridgeAPI?.sendCmd({
          type: 'send_file',
          space_id: spaceId,
          fileName: file.name,
          data: base64Data,
          tag: tag || 'default'
        });
        
        // Примечание: Мы НЕ делаем оптимистичное обновление для файла здесь,
        // так как ждем подтверждения от Python (new_file_message), чтобы показать реальный путь и размер.
      };
      reader.readAsDataURL(file.raw);
    }
  };

  const handleOpenSpaceInfo = (space) => {
    setSelectedSpaceInfo(space);
    setSpaceInfoOpen(true);
  };

  const handleDeleteSpace = (spaceId) => {
    if (window.confirm('Вы уверены, что хотите удалить это пространство?')) {
        window.bridgeAPI?.sendCmd({ type: 'delete_space', id: spaceId });
        if (activeSpaceId === spaceId) setActiveSpaceId(null);
    }
  };

  // --- Рендер ---

  if (appState === 'loading') {
    return <div className="loading-screen"><p>Инициализация P2P ядра...</p></div>;
  }

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
          
          {/* Используем новый ChatArea */}
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