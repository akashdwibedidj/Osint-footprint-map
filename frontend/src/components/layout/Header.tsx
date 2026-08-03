interface HeaderProps {
  toolLabel: string;
  backendStatus: "checking" | "online" | "offline";
}

export default function Header({ toolLabel, backendStatus }: HeaderProps) {
  const statusColor =
    backendStatus === "online"
      ? "bg-emerald-400"
      : backendStatus === "offline"
      ? "bg-red-500"
      : "bg-yellow-500";

  const statusText =
    backendStatus === "online"
      ? "BACKEND ONLINE"
      : backendStatus === "offline"
      ? "BACKEND OFFLINE"
      : "CHECKING...";

  return (
    <header className="h-14 shrink-0 border-b border-zinc-800 bg-zinc-950 flex items-center justify-between px-6">
      <h2 className="text-zinc-200 font-mono text-sm">{toolLabel}</h2>
      <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
        <span className={`w-2 h-2 rounded-full ${statusColor} animate-pulse`} />
        {statusText}
      </div>
    </header>
  );
}