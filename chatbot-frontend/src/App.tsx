import React from 'react';
import Chatbot from './components/Chatbot';
import './App.css';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100">
      <div className="container mx-auto px-4 py-10">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-semibold text-slate-100 mb-2">
            AI Appointment Assistant
          </h1>
          <p className="text-lg text-slate-300">
            Book your appointments with our intelligent chatbot
          </p>
        </div>

        <div className="max-w-4xl mx-auto">
          <Chatbot />
        </div>
      </div>
    </div>
  );
}

export default App;