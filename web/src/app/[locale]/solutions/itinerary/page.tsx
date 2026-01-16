import { Link } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AnimatedFlowDiagram } from "@/components/AnimatedFlowDiagram";
import { ItineraryExample } from "@/components/ItineraryExample";
import { ChevronLeft } from "lucide-react";

export default function ItineraryHome() {
  const t = useTranslations();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-1 text-muted-foreground hover:text-foreground transition-colors">
              <ChevronLeft className="h-4 w-4" />
              <span className="text-sm">{t("common.appName")}</span>
            </Link>
            <span className="text-muted-foreground">/</span>
            <h1 className="text-xl font-bold">{t("home.solutionName")}</h1>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link href="/solutions/itinerary/generate">
              <Button>{t("common.getStarted")}</Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-16 md:py-24">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
            {t("home.title")}
          </h2>
          <p className="text-xl text-muted-foreground">
            {t("home.subtitle")}
          </p>
          <Link href="/solutions/itinerary/generate">
            <Button size="lg" className="text-lg px-8 py-6">
              {t("home.cta")}
            </Button>
          </Link>
        </div>

        {/* Features */}
        <div className="mt-24 grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          <FeatureCard
            title={t("home.features.smartOrganization.title")}
            description={t("home.features.smartOrganization.description")}
            icon={
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
                />
              </svg>
            }
          />
          <FeatureCard
            title={t("home.features.richContent.title")}
            description={t("home.features.richContent.description")}
            icon={
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                />
              </svg>
            }
          />
          <FeatureCard
            title={t("home.features.multiLanguage.title")}
            description={t("home.features.multiLanguage.description")}
            icon={
              <svg className="h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
                />
              </svg>
            }
          />
        </div>

        {/* How it works */}
        <div className="mt-24 max-w-3xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-12">{t("home.howItWorks.title")}</h3>
          <div className="space-y-8">
            <Step number={1} title={t("home.howItWorks.step1.title")}>
              {t("home.howItWorks.step1.description")}
            </Step>
            <Step number={2} title={t("home.howItWorks.step2.title")}>
              {t("home.howItWorks.step2.description")}
            </Step>
            <Step number={3} title={t("home.howItWorks.step3.title")}>
              {t("home.howItWorks.step3.description")}
            </Step>
          </div>
        </div>

        {/* Interactive Flow */}
        <div className="mt-24 max-w-4xl mx-auto">
          <div className="bg-card rounded-xl p-8 shadow-sm border">
            <h3 className="text-2xl font-bold text-center mb-4">
              {t("home.interactiveFlow.title")}
            </h3>
            <p className="text-center text-muted-foreground mb-8 max-w-2xl mx-auto">
              {t("home.interactiveFlow.description")}
            </p>
            <AnimatedFlowDiagram
              steps={[
                { icon: "input", label: t("home.interactiveFlow.steps.input") },
                { icon: "ai", label: t("home.interactiveFlow.steps.ai") },
                { icon: "approval", label: t("home.interactiveFlow.steps.approval") },
                { icon: "research", label: t("home.interactiveFlow.steps.research") },
                { icon: "document", label: t("home.interactiveFlow.steps.document") },
              ]}
            />
            <p className="text-center text-sm text-muted-foreground mt-6 italic">
              {t("home.interactiveFlow.note")}
            </p>
          </div>
        </div>

        {/* Example Section */}
        <div className="mt-24 max-w-5xl mx-auto">
          <h3 className="text-2xl font-bold text-center mb-4">
            {t("home.example.title")}
          </h3>
          <p className="text-center text-muted-foreground mb-12 max-w-2xl mx-auto">
            {t("home.example.subtitle")}
          </p>
          <div className="relative">
            <ItineraryExample />
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

function FeatureCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-card rounded-lg p-6 shadow-sm border">
      <div className="text-primary mb-4">{icon}</div>
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}

function Step({
  number,
  title,
  children,
}: {
  number: number;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold">
        {number}
      </div>
      <div>
        <h4 className="font-semibold text-lg">{title}</h4>
        <p className="text-muted-foreground">{children}</p>
      </div>
    </div>
  );
}
