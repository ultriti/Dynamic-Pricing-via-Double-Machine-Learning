import React from "react";
import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import HomePage from "./HomePage/HomePage";
import UploadPage from "./UploadPage/UploadPage";
import EDAPage from "./EDAPage/EDAPage";
import "./App.css";

const App = () => {
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
};

export default App;
