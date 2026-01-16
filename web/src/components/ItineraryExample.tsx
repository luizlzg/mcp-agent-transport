"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Ticket, Link2, ArrowRight } from "lucide-react";

// Rome attraction images from Unsplash
const IMAGES = {
  colosseum: "https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=600&h=400&fit=crop",
  forum: "https://images.unsplash.com/photo-1555992828-ca4dbe41d294?w=600&h=400&fit=crop",
  trevi: "https://images.unsplash.com/photo-1525874684015-58379d421a52?w=600&h=400&fit=crop",
  pantheon: "https://images.unsplash.com/photo-1583175192029-3f1f32b6a51e?w=600&h=400&fit=crop",
  vatican: "https://images.unsplash.com/photo-1531572753322-ad063cecc140?w=600&h=400&fit=crop",
  stpeters: "https://images.unsplash.com/photo-1558004818-4dd1c1416c43?w=600&h=400&fit=crop",
};

// Day configurations with attraction keys
const DAYS_CONFIG = [
  { day: 1, attractions: ["colosseum", "forum"] },
  { day: 2, attractions: ["trevi", "pantheon"] },
  { day: 3, attractions: ["vatican", "stpeters"] },
];

export function ItineraryExample() {
  const t = useTranslations("home.example");
  const [selectedDay, setSelectedDay] = useState(1);

  const currentDayConfig = DAYS_CONFIG.find(d => d.day === selectedDay)!;
  const firstAttraction = currentDayConfig.attractions[0];

  return (
    <div className="grid md:grid-cols-2 gap-8 items-start">
      {/* Input Side */}
      <div className="space-y-4">
        <h4 className="text-lg font-semibold text-muted-foreground">
          {t("input.title")}
        </h4>
        <div className="bg-muted/50 rounded-lg p-6 font-mono text-sm border border-dashed whitespace-pre-line">
          {t("input.content")}
        </div>
      </div>

      {/* Arrow (hidden on mobile) */}
      <div className="hidden md:flex absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10">
        <div className="bg-primary rounded-full p-3 shadow-lg">
          <ArrowRight className="h-6 w-6 text-primary-foreground" />
        </div>
      </div>

      {/* Output Side */}
      <div className="space-y-4">
        <h4 className="text-lg font-semibold text-muted-foreground">
          {t("output.title")}
        </h4>
        <div className="bg-card rounded-lg border shadow-sm overflow-hidden">
          {/* Day Tabs */}
          <div className="flex border-b bg-muted/30">
            {DAYS_CONFIG.map(({ day }) => (
              <button
                key={day}
                onClick={() => setSelectedDay(day)}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                  selectedDay === day
                    ? "bg-background text-primary border-b-2 border-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {t(`output.days.${day}.title`).split(" - ")[0]}
              </button>
            ))}
          </div>

          {/* Day Title */}
          <div className="bg-primary/10 px-4 py-3 border-b">
            <h5 className="font-semibold text-primary">
              {t(`output.days.${selectedDay}.title`)}
            </h5>
          </div>

          {/* Featured Attraction */}
          <div className="p-4">
            {/* Attraction Image */}
            <img
              src={IMAGES[firstAttraction as keyof typeof IMAGES]}
              alt={t(`output.days.${selectedDay}.${firstAttraction}.name`)}
              className="w-full h-48 object-cover rounded-lg mb-4"
            />

            {/* Attraction Name */}
            <h6 className="font-bold text-lg text-foreground border-b pb-2 mb-3">
              {t(`output.days.${selectedDay}.${firstAttraction}.name`)}
            </h6>

            {/* Description */}
            <p className="text-sm text-muted-foreground mb-4">
              {t(`output.days.${selectedDay}.${firstAttraction}.description`)}
            </p>

            {/* Ticket Info Section */}
            <div className="mb-4">
              <h6 className="text-sm font-semibold text-secondary flex items-center gap-2 mb-2">
                <Ticket className="h-4 w-4" />
                {t("output.ticketInfo")}
              </h6>
              <div className="pl-6 space-y-1">
                <p className="text-sm text-muted-foreground">
                  {t(`output.days.${selectedDay}.${firstAttraction}.ticketInfo`)}
                </p>
                <p className="text-sm font-medium">
                  {t(`output.days.${selectedDay}.${firstAttraction}.ticketPrice`)}
                </p>
              </div>
            </div>

            {/* Useful Links Section */}
            <div className="mb-4">
              <h6 className="text-sm font-semibold text-secondary flex items-center gap-2 mb-2">
                <Link2 className="h-4 w-4" />
                {t("output.usefulLinks")}
              </h6>
              <div className="pl-6 space-y-1">
                {(t.raw(`output.days.${selectedDay}.${firstAttraction}.links`) as string[]).map((link, idx) => (
                  <p key={idx} className="text-sm text-primary hover:underline cursor-pointer">
                    {link}
                  </p>
                ))}
              </div>
            </div>

            {/* Estimated Cost */}
            <div className="flex items-center justify-between pt-3 border-t">
              <span className="text-sm text-muted-foreground">{t("output.estimatedCost")}</span>
              <span className="font-semibold text-primary">
                {t(`output.days.${selectedDay}.${firstAttraction}.cost`)}/{t("output.perPerson")}
              </span>
            </div>
          </div>

          {/* More attractions indicator */}
          <div className="px-4 py-3 bg-muted/30 text-center text-sm text-muted-foreground border-t">
            + {currentDayConfig.attractions.length - 1} {t("output.moreAttractions")}
          </div>
        </div>
      </div>
    </div>
  );
}
