import { useEffect, useState, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api/client";

interface GraphNode {
  id: string;
  label: string;
  type: "Target" | "Identifier" | "Platform";
}

interface GraphEdge {
  source: string;
  target: string;
  type: string;
  url?: string | null;
}

interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

interface GraphViewProps {
  username: string | null;
  toolId?: string;
}

const GRAPH_ENDPOINTS: Record<string, (u: string) => string> = {
  sherlock: (u) => `/scan/graph/${u}`,
  maigret: (u) => `/maigret/graph/${u}`,
};

const nodeColor: Record<string, string> = {
  Target: "#f59e0b",
  Identifier: "#10b981",
  Platform: "#3b82f6",
};

export default function GraphView({ username, toolId }: GraphViewProps) {
  const [data, setData] = useState<GraphData>({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraph = useCallback(async (target: string) => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = toolId && GRAPH_ENDPOINTS[toolId]
        ? GRAPH_ENDPOINTS[toolId](target)
        : `/scan/graph/${target}`;
      const res = await api.get<GraphData>(endpoint);
      setData(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load graph.");
      setData({ nodes: [], edges: [] });
    } finally {
      setLoading(false);
    }
  }, [toolId]);

  useEffect(() => {
    if (username) fetchGraph(username);
  }, [username, toolId, fetchGraph]);
  
  if (!username) {
    return (
      <p className="text-zinc-600 font-mono text-sm border border-zinc-800 rounded p-4">
        Run a scan first to see the footprint graph.
      </p>
    );
  }

  if (loading) {
    return <p className="text-zinc-500 font-mono text-sm">Loading graph...</p>;
  }

  if (error) {
    return <p className="text-red-400 font-mono text-sm">⚠ {error}</p>;
  }

  return (
    <div className="border border-zinc-800 rounded-md bg-zinc-950 overflow-hidden">
      <div className="flex gap-4 px-4 py-2 border-b border-zinc-800 text-xs font-mono text-zinc-400">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: nodeColor.Target }} />
          Target
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: nodeColor.Identifier }} />
          Identifier
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: nodeColor.Platform }} />
          Platform
        </span>
      </div>

      <ForceGraph2D
        graphData={{
          nodes: data.nodes.map((n) => ({ ...n })),
          links: data.edges.map((e) => ({ ...e })),
        }}
        nodeLabel={(node: any) => `${node.type}: ${node.label}`}
        nodeColor={(node: any) => nodeColor[node.type] || "#71717a"}
        linkColor={() => "rgba(255,255,255,0.2)"}
        backgroundColor="#09090b"
        height={500}
        onNodeClick={(node: any) => {
          const edge = data.edges.find((e) => e.target === node.id && e.url);
          if (edge?.url) window.open(edge.url, "_blank");
        }}
      />
    </div>
  );
}