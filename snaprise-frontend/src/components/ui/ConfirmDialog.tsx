"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { Modal } from "./Modal";

interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  /** Renders the confirm button in a destructive (red) style. */
  danger?: boolean;
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  loading = false,
  danger = false,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} onClose={onClose} size="sm">
      <div className="flex flex-col gap-4 px-6 pb-2 pt-6">
        <div
          className={`flex h-12 w-12 items-center justify-center rounded-full ${
            danger ? "bg-red-50 text-red-500" : "bg-input text-foreground/70"
          }`}
        >
          <AlertTriangle className="h-6 w-6" />
        </div>
        <div>
          <h2 className="text-lg font-bold tracking-tight">{title}</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-foreground/55">
            {message}
          </p>
        </div>
      </div>
      <div className="mt-4 flex items-center gap-3 border-t border-border bg-input/60 px-6 py-4">
        <button
          onClick={onClose}
          disabled={loading}
          className="flex-1 rounded-xl border border-border bg-card py-2.5 text-sm font-medium text-foreground/70 transition-colors hover:text-foreground disabled:opacity-50"
        >
          {cancelLabel}
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 ${
            danger ? "bg-red-500" : "bg-foreground text-background"
          }`}
        >
          {loading && <Loader2 className="h-4 w-4 animate-spin" />}
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
