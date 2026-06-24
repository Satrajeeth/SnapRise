"use client";

import { Board } from "@/types/board";
import Link from "next/link";
import { ArrowRight, LayoutDashboard } from "lucide-react";

interface BoardCardProps {
  board: Board;
  /** stagger index for the entrance animation */
  index?: number;
}

export function BoardCard({ board, index = 0 }: BoardCardProps) {
  return (
    <Link href={`/dashboard/boards/${board.id}`} className="group block">
      <div
        className="animate-rise h-full rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:-translate-y-1 hover:border-foreground/30 hover:shadow-[0_12px_32px_-16px_rgba(0,0,0,0.25)] dark:hover:shadow-[0_12px_32px_-12px_rgba(0,0,0,0.7)]"
        style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
      >
        <div className="flex h-full flex-col">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-input text-foreground transition-colors duration-300 group-hover:border-foreground/20">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            <ArrowRight className="h-5 w-5 -translate-x-1.5 text-foreground/40 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
          </div>

          <h3 className="mb-2 text-lg font-semibold tracking-tight">
            {board.name}
          </h3>
          <p className="line-clamp-2 text-sm text-foreground/50">
            {board.description || "No description provided."}
          </p>

          <div className="mt-auto pt-5 text-xs font-medium text-foreground/40">
            {board.columns?.length || 0} Columns
          </div>
        </div>
      </div>
    </Link>
  );
}
