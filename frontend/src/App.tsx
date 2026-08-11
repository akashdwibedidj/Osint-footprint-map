import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Shell from "./components/layout/Shell";
import SherlockView from "./components/tools/sherlock/SherlockView";
import MaigretView from "./components/tools/maigret/MaigretView";
import HaveIBeenPwnedView from "./components/tools/haveibeenpwned/HaveIBeenPwnedView";
import ExifExtractorView from "./components/tools/exif_extractor/ExifExtractorView";
import GitleakScannerView from "./components/tools/gitleak_scanner/GitleakScannerView";
import InstaloaderView from "./components/tools/instaloader/InstaloaderView";

import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<Navigate to="/tools/sherlock" replace />} />
          <Route path="/tools/sherlock" element={<SherlockView />} />
          <Route path="/tools/maigret" element={<MaigretView />} />
          <Route path="/tools/haveibeenpwned" element={<HaveIBeenPwnedView />} />
          <Route path="/tools/exif_extractor" element={<ExifExtractorView />} />
          <Route path="/tools/gitleak_scanner" element={<GitleakScannerView />} />
          <Route path="/tools/instaloader" element={<InstaloaderView />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}

export default App;