import { cn } from "@/lib/utils";
import type { LeadStatus } from "@/types/api/admin.types";

// Color-coded pill for a lead's lifecycle status. Colors are intentionally
// literal (not theme tokens) so the status reads at a glance in both themes.
const STYLES: Record<LeadStatus, string> = {
  new: "bg-blue-50 text-blue-600 border-blue-100 dark:bg-blue-500/10 dark:text-blue-300 dark:border-blue-500/20",
  contacted:
    "bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/20",
  converted:
    "bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/20",
};

export function StatusBadge({ status }: { status: LeadStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize",
        STYLES[status]
      )}
    >
      {status}
    </span>
  );
}
