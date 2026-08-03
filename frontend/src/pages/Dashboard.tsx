import { useState, useEffect, useCallback } from "react";
import Sidebar from "../components/layout/Sidebar";
import Header from "../components/layout/Header";
import ScanForm from "../components/ScanForm";
import FindingsTable from "../components/FindingsTable";
import GraphView from "../components/GraphView";
import { api } from "../api/client";
import { TOOLS } from "../config/tools";
import type { Finding, FindingsResponse } from "../types";
import History from "../components/History";

type ViewMode = "table" | "graph";

export default function Dashboard() {
  const [activeToolId, setActiveToolId] = useState(TOOLS[0].id);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [lastQuery, setLastQuery] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  const activeTool = TOOLS.find((t) => t.id === activeToolId)!;

  useEffect(() => {
    api
      .get("/health")
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

    const fetchFindings = useCallback(
    async (input: string, toolId?: string) => {
      if (toolId && toolId !== activeToolId) {
        const tool = TOOLS.find((t) => t.id === toolId);
        if (tool) setActiveToolId(toolId);
      }
      
      const tool = TOOLS.find((t) => t.id === (toolId || activeToolId)) || activeTool;
      
      setLoadingFindings(true);
      try {
        const res = await api.get<FindingsResponse>(tool.fetchEndpoint(input));
        setFindings(res.data.findings);
        setLastQuery(input);
      } catch {
        setFindings([]);
      } finally {
        setLoadingFindings(false);
      }
    },
    [activeToolId, activeTool]
  );

const handleSelectTool = (id: string) => {
  setActiveToolId(id);
  // If we have a query, fetch for the new tool
  if (lastQuery) {
    fetchFindings(lastQuery, id);
  }
};

  return (
    <div className="flex bg-black min-h-screen">
      <Sidebar tools={TOOLS} activeToolId={activeToolId} onSelectTool={handleSelectTool} />

      <div className="flex-1 flex flex-col">
        <Header toolLabel={activeTool.label} backendStatus={backendStatus} />

        <main className="flex-1 p-6 overflow-y-auto">
          
          <History onSelect={(username, toolId) => fetchFindings(username, toolId)} />

          <ScanForm tool={activeTool} onScanComplete={fetchFindings} />

          {lastQuery && (
            <div className="flex items-center justify-between mb-3">
              <p className="text-zinc-500 font-mono text-xs">
                Showing results for: <span className="text-zinc-300">{lastQuery}</span>
              </p>
              <div className="flex gap-1 border border-zinc-800 rounded overflow-hidden">
                <button
                  onClick={() => setViewMode("table")}
                  className={`px-3 py-1 text-xs font-mono ${
                    viewMode === "table"
                      ? "bg-emerald-600 text-white"
                      : "bg-zinc-900 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Table
                </button>
                <button
                  onClick={() => setViewMode("graph")}
                  className={`px-3 py-1 text-xs font-mono ${
                    viewMode === "graph"
                      ? "bg-emerald-600 text-white"
                      : "bg-zinc-900 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Graph
                </button>
              </div>
            </div>
          )}

          {lastQuery && viewMode === "graph" ? (
            <GraphView username={lastQuery} toolId={activeToolId} />  // ADD toolId here
          ) : (
            <FindingsTable findings={findings} loading={loadingFindings} toolId={activeToolId} />
          )}
        </main>
      </div>
    </div>
  );
}