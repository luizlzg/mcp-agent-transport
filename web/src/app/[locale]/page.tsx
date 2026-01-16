import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { MapPin, Sparkles, ArrowRight } from "lucide-react";

export default function TravelerAIHome() {
  const t = useTranslations();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
            {t("common.appName")}
          </h1>
          <ThemeToggle />
        </nav>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-16 md:py-24">
        <div className="max-w-4xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full text-primary text-sm font-medium">
            <Sparkles className="h-4 w-4" />
            {t("common.tagline")}
          </div>
          <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
            {t("travelerHome.title")}
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            {t("travelerHome.subtitle")}
          </p>
        </div>

        {/* Solutions */}
        <div className="mt-24 max-w-5xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-12">
            {t("travelerHome.solutions.title")}
          </h3>
          <div className="grid md:grid-cols-2 gap-8">
            {/* Itinerary Generator - Main Solution */}
            <Link href="/solutions/itinerary" className="group">
              <div className="bg-card rounded-xl p-8 shadow-sm border hover:border-primary/50 hover:shadow-md transition-all h-full">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors">
                  <MapPin className="h-7 w-7 text-primary" />
                </div>
                <h4 className="text-xl font-semibold mb-3">
                  {t("travelerHome.solutions.itinerary.title")}
                </h4>
                <p className="text-muted-foreground mb-6">
                  {t("travelerHome.solutions.itinerary.description")}
                </p>
                <div className="flex items-center text-primary font-medium group-hover:gap-3 gap-2 transition-all">
                  {t("travelerHome.solutions.itinerary.cta")}
                  <ArrowRight className="h-4 w-4" />
                </div>
              </div>
            </Link>

            {/* Coming Soon Placeholder */}
            <div className="bg-card/50 rounded-xl p-8 shadow-sm border border-dashed">
              <div className="w-14 h-14 rounded-xl bg-muted flex items-center justify-center mb-6">
                <Sparkles className="h-7 w-7 text-muted-foreground" />
              </div>
              <h4 className="text-xl font-semibold mb-3 text-muted-foreground">
                {t("travelerHome.solutions.comingSoon.title")}
              </h4>
              <p className="text-muted-foreground/70">
                {t("travelerHome.solutions.comingSoon.description")}
              </p>
            </div>
          </div>
        </div>

        {/* Features Preview */}
        <div className="mt-24 max-w-4xl mx-auto">
          <div className="bg-gradient-to-br from-primary/5 to-primary/10 rounded-2xl p-8 md:p-12 text-center">
            <h3 className="text-2xl font-bold mb-4">{t("travelerHome.whyChoose.title")}</h3>
            <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
              {t("travelerHome.whyChoose.description")}
            </p>
            <div className="grid md:grid-cols-3 gap-6 text-left">
              <div className="bg-background/80 rounded-lg p-4">
                <h4 className="font-semibold mb-2">{t("travelerHome.whyChoose.feature1.title")}</h4>
                <p className="text-sm text-muted-foreground">{t("travelerHome.whyChoose.feature1.description")}</p>
              </div>
              <div className="bg-background/80 rounded-lg p-4">
                <h4 className="font-semibold mb-2">{t("travelerHome.whyChoose.feature2.title")}</h4>
                <p className="text-sm text-muted-foreground">{t("travelerHome.whyChoose.feature2.description")}</p>
              </div>
              <div className="bg-background/80 rounded-lg p-4">
                <h4 className="font-semibold mb-2">{t("travelerHome.whyChoose.feature3.title")}</h4>
                <p className="text-sm text-muted-foreground">{t("travelerHome.whyChoose.feature3.description")}</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="container mx-auto px-4 py-8 border-t mt-20">
        <p className="text-center text-muted-foreground">{t("common.poweredBy")}</p>
      </footer>
    </div>
  );
}
