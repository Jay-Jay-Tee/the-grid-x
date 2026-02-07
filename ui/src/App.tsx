import React from 'react';
import Marketplace from './components/Marketplace';
import './styles/App.css';

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>Grid-X</h1>
      </header>
      <main>
        <Marketplace />
      </main>
    </div>
  );
}
