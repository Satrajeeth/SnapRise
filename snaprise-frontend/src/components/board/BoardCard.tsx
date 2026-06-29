"use client";

import { Board } from "@/types/board";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  LayoutDashboard,
  MoreHorizontal,
  ExternalLink,
  Settings,
  Bookmark,
  Trash2,
} from "lucide-react";

interface BoardCardProps {
  board: Board;
  index?: number;
  onSettings?: (board: Board) => void;
  onSaveTemplate?: (board: Board) => void;
  onDelete?: (board: Board) => void;
}

export function BoardCard({
  board,
  index = 0,
  onSettings,
  onSaveTemplate,
  onDelete,
}: BoardCardProps) {
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const hasMenu = onSettings || onSaveTemplate || onDelete;

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node))
        setMenuOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const stop = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <Link href={`/dashboard/boards/${board.id}`} className="group relative block">
      <div
        className="animate-rise h-full rounded-2xl border border-border bg-card p-6 transition-all duration-300 hover:-translate-y-1 hover:border-foreground/30 hover:shadow-[0_12px_32px_-16px_rgba(0,0,0,0.25)] dark:hover:shadow-[0_12px_32px_-12px_rgba(0,0,0,0.7)]"
        style={{ animationDelay: `${Math.min(index, 8) * 60}ms` }}
      >
        <div className="flex h-full flex-col">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-input text-foreground transition-colors duration-300 group-hover:border-foreground/20">
              <LayoutDashboard className="h-5 w-5" />
            </div>
            {hasMenu ? (
              <button
                onClick={(e) => {
                  stop(e);
                  setMenuOpen((v) => !v);
                }}
                className="rounded-lg p-1.5 text-foreground/40 transition-colors hover:bg-input hover:text-foreground"
              >
                <MoreHorizontal className="h-5 w-5" />
              </button>
            ) : (
              <ArrowRight className="h-5 w-5 -translate-x-1.5 text-foreground/40 opacity-0 transition-all duration-300 group-hover:translate-x-0 group-hover:opacity-100" />
            )}
          </div>

          <h3 className="mb-2 text-lg font-semibold tracking-tight">{board.name}</h3>
          <p className="line-clamp-2 text-sm text-foreground/50">
            {board.description || "No description provided."}
          </p>

          <div className="mt-auto pt-5 text-xs font-medium text-foreground/40">
            {board.columns?.length || 0} Columns
          </div>
        </div>
      </div>

      {menuOpen && (
        <div
          ref={menuRef}
          onClick={stop}
          className="absolute right-4 top-14 z-30 w-52 rounded-xl border border-border bg-card p-1.5 shadow-xl"
        >
          <Item
            icon={<ExternalLink className="h-4 w-4" />}
            label="Open board"
            onClick={() => {
              setMenuOpen(false);
              router.push(`/dashboard/boards/${board.id}`);
            }}
          />
          {onSettings && (
            <Item
              icon={<Settings className="h-4 w-4" />}
              label="Settings"
              onClick={() => {
                setMenuOpen(false);
                onSettings(board);
              }}
            />
          )}
          {onSaveTemplate && (
            <Item
              icon={<Bookmark className="h-4 w-4" />}
              label="Save as template"
              onClick={() => {
                setMenuOpen(false);
                onSaveTemplate(board);
              }}
            />
          )}
          {onDelete && (
            <>
              <div className="my-1 h-px bg-border" />
              <Item
                icon={<Trash2 className="h-4 w-4" />}
                label="Delete board"
                danger
                onClick={() => {
                  setMenuOpen(false);
                  onDelete(board);
                }}
              />
            </>
          )}
        </div>
      )}
    </Link>
  );
}

function Item({
  icon,
  label,
  onClick,
  danger,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors hover:bg-input ${
        danger ? "text-red-500" : "text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
