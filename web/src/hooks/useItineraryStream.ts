"use client";

import { useState, useCallback } from "react";
import { startGeneration, getStreamUrl, submitUserResponse } from "@/lib/api";
import type { GenerateFormData, JobResult, JobStatus, ProgressStep } from "@/types/itinerary";

const INITIAL_STEPS: ProgressStep[] = [
  { id: "day_organizer", label: "Organizing attractions by day", status: "pending" },
  { id: "attraction_researcher", label: "Researching attraction details", status: "pending" },
  { id: "build_document", label: "Generating document", status: "pending" },
  { id: "finalize", label: "Finalizing itinerary", status: "pending" },
];

interface DayItinerary {
  day: number;
  attractions: string[];
}

export interface ApprovalPromptData {
  type: string;
  itinerary: DayItinerary[] | string;
  message: string;
}

export interface UseItineraryStreamReturn {
  jobId: string | null;
  status: JobStatus;
  steps: ProgressStep[];
  currentDetail: string;
  progress: number;
  result: JobResult | null;
  error: string | null;
  approvalPrompt: ApprovalPromptData | null;
  isSubmittingResponse: boolean;
  startGeneration: (formData: GenerateFormData) => Promise<void>;
  submitApproval: (approved: boolean, feedback?: string) => Promise<void>;
  reset: () => void;
}

export function useItineraryStream(): UseItineraryStreamReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus>("idle");
  const [steps, setSteps] = useState<ProgressStep[]>(INITIAL_STEPS);
  const [currentDetail, setCurrentDetail] = useState("");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approvalPrompt, setApprovalPrompt] = useState<ApprovalPromptData | null>(null);
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);

  const updateStepStatus = useCallback(
    (stepId: string, stepStatus: "pending" | "in_progress" | "completed") => {
      setSteps((prev) =>
        prev.map((step) => (step.id === stepId ? { ...step, status: stepStatus } : step))
      );
    },
    []
  );

  const reset = useCallback(() => {
    setJobId(null);
    setStatus("idle");
    setSteps(INITIAL_STEPS);
    setCurrentDetail("");
    setProgress(0);
    setResult(null);
    setError(null);
    setApprovalPrompt(null);
    setIsSubmittingResponse(false);
  }, []);

  const handleStream = useCallback(
    (id: string) => {
      const eventSource = new EventSource(getStreamUrl(id));

      eventSource.addEventListener("job_started", () => {
        setProgress(5);
        setCurrentDetail("System initialized, starting processing...");
      });

      eventSource.addEventListener("step_started", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "");
        if (data.step) {
          updateStepStatus(data.step, "in_progress");
        }
      });

      eventSource.addEventListener("step_completed", (e) => {
        const data = JSON.parse(e.data);
        if (data.step) {
          updateStepStatus(data.step, "completed");
        }
        setProgress((prev) => Math.min(prev + 15, 85));
      });

      eventSource.addEventListener("day_organizing", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "Organizing attractions...");
        updateStepStatus("day_organizer", "in_progress");
        setProgress(15);
      });

      eventSource.addEventListener("day_researching", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "Researching attractions...");
        updateStepStatus("day_organizer", "completed");
        updateStepStatus("attraction_researcher", "in_progress");
        setProgress(35);
      });

      eventSource.addEventListener("attraction_researched", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "Processing attraction...");
        setProgress((prev) => Math.min(prev + 5, 70));
      });

      eventSource.addEventListener("document_generating", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "Generating document...");
        updateStepStatus("attraction_researcher", "completed");
        updateStepStatus("build_document", "in_progress");
        setProgress(75);
      });

      eventSource.addEventListener("document_ready", (e) => {
        const data = JSON.parse(e.data);
        updateStepStatus("build_document", "completed");
        updateStepStatus("finalize", "in_progress");
        setProgress(90);
        setResult({
          documentPath: data.document_path,
          costs: data.costs || {},
        });
      });

      eventSource.addEventListener("email_sending", (e) => {
        const data = JSON.parse(e.data);
        setCurrentDetail(data.message || "Sending email...");
      });

      eventSource.addEventListener("email_sent", (e) => {
        const data = JSON.parse(e.data);
        setResult((prev) =>
          prev
            ? {
                ...prev,
                emailSent: data.success,
                emailError: data.success ? undefined : data.error,
              }
            : null
        );
      });

      eventSource.addEventListener("user_input_required", (e) => {
        const data = JSON.parse(e.data);
        setApprovalPrompt({
          type: data.type,
          itinerary: data.itinerary,
          message: data.message,
        });
        setStatus("awaiting_input");
        setCurrentDetail(data.message || "Awaiting your approval...");
        eventSource.close();
      });

      eventSource.addEventListener("job_completed", () => {
        updateStepStatus("finalize", "completed");
        setProgress(100);
        setStatus("completed");
        setCurrentDetail("Itinerary ready!");
        eventSource.close();
      });

      eventSource.addEventListener("job_failed", (e) => {
        const data = JSON.parse(e.data);
        setError(data.error || "An unknown error occurred");
        setStatus("error");
        setCurrentDetail("");
        eventSource.close();
      });

      eventSource.onerror = (event) => {
        // Only set error if the connection was not intentionally closed
        // EventSource.CLOSED = 2
        if (eventSource.readyState === EventSource.CLOSED) {
          return; // Already closed, likely intentionally
        }
        console.error("EventSource error:", event);
        setError("Connection lost. Please try again.");
        setStatus("error");
        eventSource.close();
      };

      return eventSource;
    },
    [updateStepStatus]
  );

  const start = useCallback(
    async (formData: GenerateFormData) => {
      setStatus("loading");
      setError(null);
      setSteps(INITIAL_STEPS);
      setProgress(0);
      setResult(null);
      setCurrentDetail("Starting generation...");
      setApprovalPrompt(null);

      try {
        const response = await startGeneration({
          attractions: formData.attractions,
          preferences: formData.preferences,
          num_days: formData.numDays,
          language: formData.language,
          email: formData.sendEmail && formData.email ? formData.email : null,
          send_email: formData.sendEmail,
        });

        setJobId(response.job_id);
        setStatus("streaming");
        handleStream(response.job_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to start generation");
        setStatus("error");
      }
    },
    [handleStream]
  );

  const submitApproval = useCallback(
    async (approved: boolean, feedback?: string) => {
      if (!jobId) return;

      setIsSubmittingResponse(true);

      try {
        const response = approved ? "yes" : feedback || "no";
        const result = await submitUserResponse(jobId, response);

        if (result.success) {
          setApprovalPrompt(null);
          setStatus("streaming");
          setCurrentDetail("Resuming generation...");
          // Reconnect to stream to get remaining events
          handleStream(jobId);
        } else {
          setError(result.message);
          setStatus("error");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to submit response");
        setStatus("error");
      } finally {
        setIsSubmittingResponse(false);
      }
    },
    [jobId, handleStream]
  );

  return {
    jobId,
    status,
    steps,
    currentDetail,
    progress,
    result,
    error,
    approvalPrompt,
    isSubmittingResponse,
    startGeneration: start,
    submitApproval,
    reset,
  };
}
