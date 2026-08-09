export interface Finding {
  source: string;
  source_url: string;
  category: string;
  risk_severity: string;
  discovered_at: string | null;
  extra_metadata?: Record<string, any>;  // ADD THIS LINE
}

export interface ScanResult {
  username: string;
  total_found?: number;
  postgres?: {
    target_id: string;
    scan_id: string;
    findings_stored: number;
  };
  neo4j?: {
    target: string;
    platforms_linked: number;
  };
}

export interface FindingsResponse {
  username: string;
  target_id: string;
  total_findings: number;
  findings: Finding[];
}

export interface ToolConfig { id: string; label: string }

export interface HistoryItem {
  username: string;
  target_id: string;
  tool_id: string;
  scanned_at: string | null;
  findings_count: number;
}

