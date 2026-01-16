"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

interface DayItinerary {
  day: number;
  attractions: string[];
}

interface ApprovalPromptProps {
  itinerary: DayItinerary[] | string;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isSubmitting: boolean;
}

export function ApprovalPrompt({
  itinerary,
  onApprove,
  onRequestChanges,
  isSubmitting,
}: ApprovalPromptProps) {
  const t = useTranslations();
  const [feedback, setFeedback] = useState("");
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);

  const handleRequestChanges = () => {
    if (showFeedbackInput && feedback.trim()) {
      onRequestChanges(feedback.trim());
    } else {
      setShowFeedbackInput(true);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{t("approval.title")}</CardTitle>
        <CardDescription>{t("approval.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Itinerary Preview */}
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 max-h-96 overflow-y-auto">
          {typeof itinerary === "string" ? (
            <pre className="whitespace-pre-wrap text-sm font-mono">{itinerary}</pre>
          ) : Array.isArray(itinerary) ? (
            <div className="space-y-4">
              {itinerary.map((day, dayIdx) => (
                <div key={day.day ?? dayIdx}>
                  <h3 className="font-semibold text-lg mb-2">
                    {t("approval.day")} {day.day}
                  </h3>
                  <ul className="list-disc list-inside space-y-1">
                    {day.attractions?.map((attraction, idx) => (
                      <li key={idx} className="text-sm">
                        {attraction}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : (
            <pre className="whitespace-pre-wrap text-sm font-mono">
              {JSON.stringify(itinerary, null, 2)}
            </pre>
          )}
        </div>

        {/* Feedback Input (shown when requesting changes) */}
        {showFeedbackInput && (
          <div className="space-y-2">
            <Textarea
              placeholder={t("approval.placeholder")}
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              rows={3}
              disabled={isSubmitting}
            />
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4">
          <Button
            onClick={onApprove}
            disabled={isSubmitting}
            className="flex-1"
            variant="default"
          >
            {isSubmitting ? t("approval.submitting") : t("approval.approve")}
          </Button>
          <Button
            onClick={handleRequestChanges}
            disabled={isSubmitting || (showFeedbackInput && !feedback.trim())}
            className="flex-1"
            variant="outline"
          >
            {showFeedbackInput
              ? isSubmitting
                ? t("approval.submitting")
                : t("approval.requestChanges")
              : t("approval.requestChanges")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
