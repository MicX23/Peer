import { useState } from 'react';
import '../style/WelcomeScreen.css';

export default function WelcomeScreen({ onSubmit }) {
  const [name, setName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!name.trim() || isSubmitting) return;
    
    setIsSubmitting(true);
    onSubmit(name.trim());
  };

  return (
    <div className="welcome-overlay">
      <div className="welcome-card">
        <h2 className="welcome-title">Привет!</h2>
        <p className="welcome-subtitle">Давай создадим профиль. Как тебя зовут?</p>
        
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Введи имя..."
            className="welcome-input"
            autoFocus
            maxLength={24}
          />
          <button
            type="submit"
            disabled={!name.trim() || isSubmitting}
            className="welcome-button"
          >
            {isSubmitting ? 'Создание...' : 'Создать профиль'}
          </button>
        </form>
      </div>
    </div>
  );
}