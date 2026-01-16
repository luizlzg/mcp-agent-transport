"use client";

import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { ItineraryForm } from "@/components/ItineraryForm";
import { ProgressView } from "@/components/ProgressView";
import { ResultsView } from "@/components/ResultsView";
import { ErrorView } from "@/components/ErrorView";
import { ApprovalPrompt } from "@/components/ApprovalPrompt";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { useItineraryStream } from "@/hooks/useItineraryStream";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function GeneratePage() {
  const t = useTranslations();
  const {
    jobId,
    status,
    steps,
    currentDetail,
    progress,
    result,
    error,
    approvalPrompt,
    isSubmittingResponse,
    startGeneration,
    submitApproval,
    reset,
  } = useItineraryStream();

  return (
    <ErrorBoundary>
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-card border-b">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center justify-between">
            <Link href="/solutions/itinerary" className="text-xl font-bold hover:opacity-80">
              {t("home.solutionName")}
            </Link>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              {status !== "idle" && status !== "awaiting_input" && (
                <Button variant="outline" onClick={reset}>
                  {t("common.startOver")}
                </Button>
              )}
            </div>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-12">
        {status === "idle" && <ItineraryForm onSubmit={startGeneration} isLoading={false} />}

        {status === "loading" && <ItineraryForm onSubmit={startGeneration} isLoading={true} />}

        {status === "streaming" && (
          <ProgressView steps={steps} currentDetail={currentDetail} progress={progress} />
        )}

        {status === "awaiting_input" && approvalPrompt && (
          <ApprovalPrompt
            itinerary={approvalPrompt.itinerary}
            onApprove={() => submitApproval(true)}
            onRequestChanges={(feedback) => submitApproval(false, feedback)}
            isSubmitting={isSubmittingResponse}
          />
        )}

        {status === "awaiting_input" && !approvalPrompt && (
          <ProgressView steps={steps} currentDetail="Waiting for approval data..." progress={progress} />
        )}

        {status === "completed" && jobId && result && (
          <ResultsView jobId={jobId} result={result} onReset={reset} />
        )}

        {status === "completed" && (!jobId || !result) && (
          <div className="text-center">
            <p className="text-muted-foreground">Generation completed but no result available.</p>
            <Button onClick={reset} className="mt-4">Start Over</Button>
          </div>
        )}

        {status === "error" && <ErrorView error={error || "An unknown error occurred"} onRetry={reset} />}
      </main>
    </div>
    </ErrorBoundary>
  );
}
