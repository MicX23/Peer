/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Важно для переключения тем
  theme: {
    extend: {
      colors: {
        // Discord-like palette
        discord: {
          bg: '#36393f',       // Основной фон
          sidebar: '#2f3136',  // Левая панель
          channel: '#40444b',  // Активный элемент/инпут
          text: '#dcddde',     // Основной текст
          muted: '#72767d',    // Вторичный текст
          accent: '#5865f2',   // Blurple (кнопки)
          hover: '#32353b',    // Ховер эффекты
          border: '#202225',   // Границы
        }
      }
    },
  },
  plugins: [],
}