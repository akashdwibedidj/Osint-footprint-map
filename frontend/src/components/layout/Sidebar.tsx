
import type { ToolConfig } from "../../types";

interface SidebarProps {
  tools: ToolConfig[];
  activeToolId: string;
  onSelectTool: (id: string) => void;
}

export default function Sidebar({ tools, activeToolId, onSelectTool }: SidebarProps) {
  return (
    <aside className="w-64 shrink-0 bg-zinc-950 border-r border-zinc-800 h-screen flex flex-col">
      <div className="px-4 py-5 border-b border-zinc-800">
        <h1 className="text-emerald-400 font-mono text-sm tracking-widest uppercase">
          OSINT Footprint Map
        </h1>
        <p className="text-zinc-500 text-xs mt-1 font-mono">exposure tracking console</p>
      </div>

      <nav className="flex-1 overflow-y-auto py-3">
        <p className="px-4 text-zinc-600 text-[10px] uppercase tracking-wider font-mono mb-2">
          Tools
        </p>
        {tools.map((tool) => (
          <button
            key={tool.id}
            onClick={() => onSelectTool(tool.id)}
            className={`w-full text-left px-4 py-2 text-sm font-mono transition-colors ${
              activeToolId === tool.id
                ? "bg-emerald-500/10 text-emerald-400 border-l-2 border-emerald-400"
                : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 border-l-2 border-transparent"
            }`}
          >
            {tool.label}
          </button>
        ))}
      </nav>

      <div className="px-4 py-3 border-t border-zinc-800 text-[10px] text-zinc-600 font-mono">
        {tools.length} tool{tools.length !== 1 ? "s" : ""} integrated
      </div>
    </aside>
  );
}