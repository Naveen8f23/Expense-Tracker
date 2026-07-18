// Thin API client — the ONLY place in the frontend that knows how to reach the backend.
// UI components must go through functions exported here, never call fetch() directly,
// so the backend's API Layer stays the sole door into the system (docs/ARCHITECTURE.md §3).

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface HealthStatus {
  status: string;
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await fetch(`${BASE_URL}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}
