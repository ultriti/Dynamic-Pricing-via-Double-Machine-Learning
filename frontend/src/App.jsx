import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";
import { LoadingSpinner } from "./components/Feedback";
import "./App.css";

const HomePage = lazy(() => import("./HomePage/HomePage"));
const UploadPage = lazy(() => import("./UploadPage/UploadPage"));
const EDAPage = lazy(() => import("./EDAPage/EDAPage"));
const DatasetPreview = lazy(() => import("./pages/DatasetPreview"));
const ModelAnalysis = lazy(() => import("./pages/ModelAnalysis"));

function App() {
  return (
    <Router>
      <div className="app-shell">
        <Navbar />
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <Suspense fallback={<LoadingSpinner />}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/eda" element={<EDAPage />} />
                <Route path="/preview" element={<DatasetPreview />} />
                <Route path="/causal" element={<ModelAnalysis />} />
              </Routes>
            </Suspense>
          </main>
        </div>
      </div>
    </Router>
  );
}

export default App;
