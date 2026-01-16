"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { ProgressStep } from "@/types/itinerary";

interface ProgressViewProps {
  steps: ProgressStep[];
  currentDetail?: string; // Kept for backwards compatibility but not displayed
  progress: number;
}

function StepIcon({ status }: { status: ProgressStep["status"] }) {
  if (status === "completed") {
    return (
      <svg
        className="h-5 w-5 text-green-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    );
  }

  if (status === "in_progress") {
    return (
      <svg className="h-5 w-5 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    );
  }

  return (
    <svg className="h-5 w-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" strokeWidth={2} />
    </svg>
  );
}

const STEP_KEYS: Record<string, string> = {
  day_organizer: "progress.steps.dayOrganizer",
  attraction_researcher: "progress.steps.attractionResearcher",
  build_document: "progress.steps.buildDocument",
  finalize: "progress.steps.finalize",
};

export function ProgressView({ steps, currentDetail, progress }: ProgressViewProps) {
  const t = useTranslations();

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{t("progress.title")}</CardTitle>
        <CardDescription>{t("progress.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Progress value={progress} className="h-2" />

        <div className="space-y-4">
          {steps.map((step) => (
            <div key={step.id} className="flex items-center space-x-3">
              <StepIcon status={step.status} />
              <span
                className={
                  step.status === "completed"
                    ? "text-green-600"
                    : step.status === "in_progress"
                    ? "text-blue-600 font-medium"
                    : "text-gray-400"
                }
              >
                {STEP_KEYS[step.id] ? t(STEP_KEYS[step.id]) : step.label}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
