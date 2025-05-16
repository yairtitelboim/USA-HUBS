import React from 'react';
import CountyMap from './components/CountyMap';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>County Obsolescence Score Visualization</h1>
      </header>
      <main>
        <CountyMap />
      </main>
    </div>
  );
}

export default App;
