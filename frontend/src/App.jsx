import HomePage from "./HomePage/HomePage";
import UploadPage from "./UploadPage/UploadPage";
import EDAPage from "./EDAPage/EDAPage";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import "./App.css"


function App() {
  return (
    <Router>
      <div className="app-layout">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/eda" element={<EDAPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
