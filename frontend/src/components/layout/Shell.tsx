import { useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { api } from "../../api/client";
import { TOOLS } from "../../config/tools";

export default function Shell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    api
      .get("/health")
      .then(() => setBackendStatus("online"))
      .catch(() => setBackendStatus("offline"));
  }, []);

  const activeToolId = location.pathname.split("/tools/")[1] || "";
  const activeTool = TOOLS.find((t) => t.id === activeToolId);

  return (
    <div className="flex bg-black min-h-screen">
      <Sidebar tools={TOOLS} activeToolId={activeToolId} />
      <div className="flex-1 flex flex-col">
        <Header toolLabel={activeTool?.label || ""} backendStatus={backendStatus} />
        <main className="flex-1 p-6 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}