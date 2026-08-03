import axios from "axios";

export const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 120000, // Sherlock-style scans can take 30-60s+
});