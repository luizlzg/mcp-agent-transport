/**
 * Type definitions for itinerary generation.
 */

export interface GenerateFormData {
  attractions: string;
  preferences: string;
  numDays: number;
  language: "en" | "pt-br" | "es" | "fr";
  email: string;
  sendEmail: boolean;
}

export interface GenerateResponse {
  job_id: string;
  stream_url: string;
  message: string;
}

export interface JobResult {
  documentPath: string;
  costs: Record<string, number>;
  emailSent?: boolean;
  emailError?: string;
}

export type JobStatus = "idle" | "loading" | "streaming" | "awaiting_input" | "completed" | "error";

export interface ProgressStep {
  id: string;
  label: string;
  status: "pending" | "in_progress" | "completed";
  detail?: string;
}

export const LANGUAGES = {
  en: "English",
  "pt-br": "Portuguese (Brazil)",
  es: "Spanish",
  fr: "French",
} as const;
