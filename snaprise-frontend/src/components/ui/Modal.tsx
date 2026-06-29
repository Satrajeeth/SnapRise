"use client";

import { motion, AnimatePresence } from "framer-motion";
import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

type ModalSize = "sm" | "md" | "lg" | "xl";

const sizes: Record<ModalSize, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-xl",
  xl: "max-w-3xl",
};

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  /** Small uppercase eyebrow shown above the title. */
  eyebrow?: string;
  size?: ModalSize;
  children: React.ReactNode;
  /** Rendered in a muted action bar at the bottom. */
  footer?: React.ReactNode;
  className?: string;
}

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  eyebrow,
  size = "md",
  children,
  footer,
  className,
}: ModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: 8 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className={cn(
              "custom-scrollbar relative z-10 flex max-h-[90vh] w-full flex-col overflow-hidden rounded-3xl border border-border bg-card shadow-2xl",
              sizes[size],
              className
            )}
          >
            {(title || eyebrow) && (
              <div className="flex shrink-0 items-start gap-3 px-6 pb-4 pt-5">
                <div className="flex-1">
                  {eyebrow && (
                    <p className="text-[11px] font-semibold tracking-wide text-foreground/40">
                      {eyebrow}
                    </p>
                  )}
                  {title && (
                    <h2 className="text-xl font-bold tracking-tight">{title}</h2>
                  )}
                  {subtitle && (
                    <p className="mt-0.5 text-sm text-foreground/50">{subtitle}</p>
                  )}
                </div>
                <button
                  onClick={onClose}
                  className="rounded-lg border border-border bg-input p-2 text-foreground/50 transition-colors hover:text-foreground"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            <div className="custom-scrollbar flex-1 overflow-y-auto">{children}</div>

            {footer && (
              <div className="flex shrink-0 items-center gap-3 border-t border-border bg-input/60 px-6 py-4">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
