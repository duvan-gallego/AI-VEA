export interface HealthResponse {
  environment: string;
  service: string;
  status: "ok";
  version: string;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/health", { signal });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
