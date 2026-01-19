/**
 * API client for the itinerary generator backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface GenerateRequest {
  attractions: string;
  preferences: string;
  num_days: number;
  language: string;
  email: string | null;
  send_email: boolean;
}

export interface GenerateResponse {
  job_id: string;
  stream_url: string;
  message: string;
}

export async function startGeneration(data: GenerateRequest): Promise<GenerateResponse> {
  const response = await fetch(`${API_URL}/api/v1/itinerary/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || "Failed to start generation");
  }

  return response.json();
}

export function getStreamUrl(jobId: string): string {
  return `${API_URL}/api/v1/itinerary/stream/${jobId}`;
}

export function getDownloadUrl(jobId: string): string {
  return `${API_URL}/api/v1/itinerary/download/${jobId}`;
}

export interface SubmitResponseResult {
  success: boolean;
  message: string;
  stream_url?: string;
}

export async function submitUserResponse(
  jobId: string,
  response: string
): Promise<SubmitResponseResult> {
  const res = await fetch(`${API_URL}/api/v1/itinerary/${jobId}/respond`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ response }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || "Failed to submit response");
  }

  return res.json();
}
