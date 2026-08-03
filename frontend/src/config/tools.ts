import type { ToolConfig } from "../types";

export const TOOLS: ToolConfig[] = [
  {
    id: "sherlock",
    label: "Sherlock — Username Search",
    inputLabel: "Username",
    inputPlaceholder: "e.g. zachking",
    scanEndpoint: (username: string) => `/scan/username/${username}`,
    fetchEndpoint: (username: string) => `/scan/username/${username}`,
    graphEndpoint: (username: string) => `/scan/graph/${username}`,
  },
  {
    id: "maigret",
    label: "Maigret — Username Search",
    inputLabel: "Username",
    inputPlaceholder: "e.g. zachking",
    scanEndpoint: (username: string) => `/maigret/username/${username}`,
    fetchEndpoint: (username: string) => `/maigret/username/${username}`,
    graphEndpoint: (username: string) => `/maigret/graph/${username}`,
  },
];