
import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import Results from './pages/Results';
import SelectClasses from './pages/SelectClasses';
import Error from './pages/Error';
import NotFoundPage from './pages/NotFoundPage'; // Import the NotFoundPage component



function App() {
  return (

    <Router>
    <div className="App">
      <Routes>
        {/* Main Routes */}
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
        <Route path="/select_classes" element={<SelectClasses />} />
        <Route path="/error" element={<Error />} />

        {/* 404 Route (catch-all) */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </div>
  </Router>
    
  );
}

export default App;
