"use client";

import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface ErrorViewProps {
  error: string;
  onRetry: () => void;
}

export function ErrorView({ error, onRetry }: ErrorViewProps) {
  const t = useTranslations();

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="mx-auto mb-4">
          <svg
            className="h-16 w-16 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <CardTitle className="text-2xl text-red-600">{t("error.title")}</CardTitle>
        <CardDescription>{t("error.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-700 dark:text-red-300">{error}</p>
        </div>

        <Button onClick={onRetry} className="w-full">
          {t("error.retry")}
        </Button>
      </CardContent>
    </Card>
  );
}
