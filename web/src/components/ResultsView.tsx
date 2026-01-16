"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Eye, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DocumentPreview } from "@/components/DocumentPreview";
import { getDownloadUrl } from "@/lib/api";
import type { JobResult } from "@/types/itinerary";

interface ResultsViewProps {
  jobId: string;
  result: JobResult;
  onReset: () => void;
}

export function ResultsView({ jobId, result, onReset }: ResultsViewProps) {
  const t = useTranslations();
  const [showPreview, setShowPreview] = useState(false);

  const handleDownload = () => {
    window.open(getDownloadUrl(jobId), "_blank");
  };

  return (
    <>
      <DocumentPreview
        jobId={jobId}
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        onDownload={handleDownload}
      />
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4">
          <svg
            className="h-16 w-16 text-green-500"
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
        </div>
        <CardTitle className="text-2xl">{t("results.title")}</CardTitle>
        <CardDescription>{t("results.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Cost Summary */}
        {Object.keys(result.costs).length > 0 && (
          <div className="bg-muted rounded-lg p-4">
            <h3 className="font-semibold mb-2">{t("results.costs.title")}</h3>
            <div className="space-y-1">
              {Object.entries(result.costs).map(([currency, amount]) => (
                <p key={currency} className="text-muted-foreground">
                  <span className="font-medium text-foreground">{currency}:</span> {amount.toFixed(2)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button onClick={() => setShowPreview(true)} variant="outline" className="flex-1" size="lg">
            <Eye className="mr-2 h-5 w-5" />
            {t("results.preview")}
          </Button>
          <Button onClick={handleDownload} className="flex-1" size="lg">
            <Download className="mr-2 h-5 w-5" />
            {t("results.download")}
          </Button>
        </div>

        {/* Email Status */}
        {result.emailSent !== undefined && (
          <div
            className={`flex items-center justify-center space-x-2 ${
              result.emailSent ? "text-green-600" : "text-red-500"
            }`}
          >
            {result.emailSent ? (
              <>
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                <span>{t("results.emailSent")}</span>
              </>
            ) : (
              <>
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span>
                  {t("results.emailFailed")}: {result.emailError || "Unknown error"}
                </span>
              </>
            )}
          </div>
        )}

        {/* Create Another */}
        <div className="pt-4 border-t">
          <Button variant="outline" onClick={onReset} className="w-full">
            {t("results.createAnother")}
          </Button>
        </div>
      </CardContent>
    </Card>
    </>
  );
}
