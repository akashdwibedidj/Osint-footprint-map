import { useEffect, useState } from "react";
import axios from "axios";

function App() {
  const [status, setStatus] = useState("checking...");

  useEffect(() => {
    axios.get("http://localhost:8000/health")
      .then(res => setStatus(res.data.status))
      .catch(() => setStatus("backend unreachable"));
  }, []);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-2">OSINT Footprint Map</h1>
        <p className="text-slate-400">Backend status: <span className="font-mono">{status}</span></p>
      </div>
    </div>
  );
}

export default App;