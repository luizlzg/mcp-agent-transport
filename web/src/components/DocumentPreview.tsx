"use client";

import { useEffect, useRef, useState } from "react";
import { X, Download, Loader2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getDownloadUrl } from "@/lib/api";

interface DocumentPreviewProps {
  jobId: string;
  isOpen: boolean;
  onClose: () => void;
  onDownload: () => void;
}

export function DocumentPreview({ jobId, isOpen, onClose, onDownload }: DocumentPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewReady, setPreviewReady] = useState(false);

  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    let mounted = true;

    const loadDocument = async () => {
      setIsLoading(true);
      setError(null);
      setPreviewReady(false);

      try {
        // Fetch the document
        const response = await fetch(getDownloadUrl(jobId));
        if (!response.ok) {
          throw new Error("Failed to fetch document");
        }

        const blob = await response.blob();

        // Dynamic import docx-preview
        const docxPreview = await import("docx-preview");

        if (!mounted || !containerRef.current) return;

        // Clear container
        containerRef.current.innerHTML = "";

        // Render document
        await docxPreview.renderAsync(blob, containerRef.current, undefined, {
          className: "docx-preview-content",
          inWrapper: true,
          ignoreWidth: false,
          ignoreHeight: false,
          ignoreFonts: false,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          experimental: true,
          trimXmlDeclaration: true,
          useBase64URL: true,
        });

        if (mounted) {
          setPreviewReady(true);
        }
      } catch (err) {
        console.error("Document preview error:", err);
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load document preview");
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadDocument();

    return () => {
      mounted = false;
    };
  }, [isOpen, jobId]);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "unset";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-5xl h-[90vh] mx-4 bg-background rounded-lg shadow-2xl flex flex-col overflow-hidden border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b bg-card">
          <h2 className="text-lg font-semibold">Document Preview</h2>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose}>
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto bg-muted/30">
          {isLoading && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading preview...</p>
            </div>
          )}

          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 gap-4">
              <div className="bg-card rounded-lg p-6 border max-w-md">
                <p className="text-muted-foreground mb-4">
                  Preview is not available for this document format.
                  Please download the file to view it.
                </p>
                <div className="flex gap-3 justify-center">
                  <Button onClick={onDownload}>
                    <Download className="h-4 w-4 mr-2" />
                    Download Document
                  </Button>
                </div>
              </div>
            </div>
          )}

          <div
            ref={containerRef}
            className={`min-h-full ${isLoading || error ? "hidden" : ""}`}
            style={{
              padding: previewReady ? "2rem" : 0,
            }}
          />
        </div>
      </div>

      {/* Global styles for docx-preview */}
      <style jsx global>{`
        .docx-preview-content {
          background: white;
          padding: 2rem;
          margin: 0 auto;
          box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
          border-radius: 0.5rem;
        }
        .docx-preview-content .docx-wrapper {
          background: white !important;
          padding: 20px !important;
        }
        .docx-preview-content section.docx {
          box-shadow: none !important;
          margin-bottom: 1rem;
        }
      `}</style>
    </div>
  );
}
