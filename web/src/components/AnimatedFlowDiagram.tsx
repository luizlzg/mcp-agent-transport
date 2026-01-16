"use client";

import { useEffect, useRef, useState } from "react";
import { MapPin, Brain, CheckCircle, FileText, Search } from "lucide-react";

interface FlowStepProps {
  icon: React.ReactNode;
  label: string;
  isActive: boolean;
  delay: number;
}

function FlowStep({ icon, label, isActive, delay }: FlowStepProps) {
  return (
    <div
      className={`flex flex-col items-center transition-all duration-500 ${
        isActive ? "opacity-100 scale-100" : "opacity-30 scale-95"
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div
        className={`w-14 h-14 md:w-16 md:h-16 rounded-full flex items-center justify-center transition-all duration-500 ${
          isActive
            ? "bg-primary text-primary-foreground shadow-lg"
            : "bg-muted text-muted-foreground"
        }`}
        style={{ transitionDelay: `${delay}ms` }}
      >
        {icon}
      </div>
      <p
        className={`mt-2 text-xs md:text-sm font-medium text-center transition-all duration-500 ${
          isActive ? "text-foreground" : "text-muted-foreground"
        }`}
        style={{ transitionDelay: `${delay + 100}ms` }}
      >
        {label}
      </p>
    </div>
  );
}

function FlowArrow({ isActive, delay }: { isActive: boolean; delay: number }) {
  return (
    <div
      className={`flex items-center px-2 md:px-4 lg:px-6 transition-all duration-500 ${
        isActive ? "opacity-100" : "opacity-30"
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <svg
        className={`w-6 h-6 md:w-8 md:h-8 transition-colors duration-500 ${
          isActive ? "text-primary" : "text-muted-foreground/50"
        }`}
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M13 7l5 5m0 0l-5 5m5-5H6"
        />
      </svg>
    </div>
  );
}

interface AnimatedFlowDiagramProps {
  steps: {
    icon: "input" | "ai" | "approval" | "research" | "document";
    label: string;
  }[];
}

const iconMap = {
  input: <MapPin className="h-6 w-6 md:h-7 md:w-7" />,
  ai: <Brain className="h-6 w-6 md:h-7 md:w-7" />,
  approval: <CheckCircle className="h-6 w-6 md:h-7 md:w-7" />,
  research: <Search className="h-6 w-6 md:h-7 md:w-7" />,
  document: <FileText className="h-6 w-6 md:h-7 md:w-7" />,
};

export function AnimatedFlowDiagram({ steps }: AnimatedFlowDiagramProps) {
  const [activeStep, setActiveStep] = useState(-1);
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isVisible) {
          setIsVisible(true);
        }
      },
      { threshold: 0.3 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, [isVisible]);

  useEffect(() => {
    if (!isVisible) return;

    // Animate through steps
    const intervals: NodeJS.Timeout[] = [];

    steps.forEach((_, index) => {
      const timeout = setTimeout(() => {
        setActiveStep(index);
      }, index * 800 + 300);
      intervals.push(timeout);
    });

    // Loop the animation
    const loopTimeout = setTimeout(() => {
      setActiveStep(-1);
      setTimeout(() => setIsVisible(false), 100);
      setTimeout(() => setIsVisible(true), 200);
    }, steps.length * 800 + 2500);
    intervals.push(loopTimeout);

    return () => intervals.forEach(clearTimeout);
  }, [isVisible, steps.length]);

  return (
    <div
      ref={containerRef}
      className="flex flex-row items-center justify-center py-6 overflow-x-auto"
    >
      {steps.map((step, index) => (
        <div key={index} className="flex items-center">
          <FlowStep
            icon={iconMap[step.icon]}
            label={step.label}
            isActive={activeStep >= index}
            delay={index * 100}
          />
          {index < steps.length - 1 && (
            <FlowArrow isActive={activeStep > index} delay={index * 100 + 200} />
          )}
        </div>
      ))}
    </div>
  );
}
