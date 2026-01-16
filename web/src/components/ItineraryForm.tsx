"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslations } from "next-intl";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { GenerateFormData } from "@/types/itinerary";

const formSchema = z.object({
  attractions: z.string().min(3),
  preferences: z.string(),
  numDays: z.number().min(1).max(14),
  language: z.enum(["en", "pt-br", "es", "fr"]),
  email: z.string().email().or(z.literal("")),
  sendEmail: z.boolean(),
});

interface ItineraryFormProps {
  onSubmit: (data: GenerateFormData) => void;
  isLoading: boolean;
}

export function ItineraryForm({ onSubmit, isLoading }: ItineraryFormProps) {
  const t = useTranslations();

  const form = useForm<GenerateFormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      attractions: "",
      preferences: "",
      numDays: 3,
      language: "en",
      email: "",
      sendEmail: false,
    },
  });

  const sendEmail = form.watch("sendEmail");

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>{t("form.title")}</CardTitle>
        <CardDescription>{t("form.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Attractions */}
          <div className="space-y-2">
            <Label htmlFor="attractions">{t("form.attractions.label")} *</Label>
            <Textarea
              id="attractions"
              placeholder={t("form.attractions.placeholder")}
              rows={6}
              {...form.register("attractions")}
            />
            {form.formState.errors.attractions && (
              <p className="text-sm text-red-500">{t("form.attractions.error")}</p>
            )}
          </div>

          {/* Preferences */}
          <div className="space-y-2">
            <Label htmlFor="preferences">{t("form.preferences.label")}</Label>
            <Textarea
              id="preferences"
              placeholder={t("form.preferences.placeholder")}
              rows={3}
              {...form.register("preferences")}
            />
          </div>

          {/* Number of Days */}
          <div className="space-y-2">
            <Label htmlFor="numDays">{t("form.numDays.label")}</Label>
            <Input
              id="numDays"
              type="number"
              min={1}
              max={14}
              className="w-24"
              {...form.register("numDays", { valueAsNumber: true })}
            />
            {form.formState.errors.numDays && (
              <p className="text-sm text-red-500">
                {form.formState.errors.numDays.type === "too_small"
                  ? t("form.numDays.errorMin")
                  : t("form.numDays.errorMax")}
              </p>
            )}
          </div>

          {/* Language */}
          <div className="space-y-2">
            <Label>{t("form.language.label")}</Label>
            <Select
              value={form.watch("language")}
              onValueChange={(value) =>
                form.setValue("language", value as GenerateFormData["language"])
              }
            >
              <SelectTrigger className="w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">{t("languages.en")}</SelectItem>
                <SelectItem value="pt-br">{t("languages.pt-br")}</SelectItem>
                <SelectItem value="es">{t("languages.es")}</SelectItem>
                <SelectItem value="fr">{t("languages.fr")}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Email Option */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="sendEmail"
                checked={sendEmail}
                onCheckedChange={(checked) => form.setValue("sendEmail", checked === true)}
              />
              <Label htmlFor="sendEmail" className="font-normal cursor-pointer">
                {t("form.email.label")}
              </Label>
            </div>

            {sendEmail && (
              <div className="ml-6">
                <Input
                  id="email"
                  type="email"
                  placeholder={t("form.email.placeholder")}
                  {...form.register("email")}
                />
                {form.formState.errors.email && (
                  <p className="text-sm text-red-500 mt-1">{t("form.email.error")}</p>
                )}
              </div>
            )}
          </div>

          {/* Submit */}
          <Button type="submit" disabled={isLoading} className="w-full">
            {isLoading ? t("form.submitting") : t("form.submit")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
