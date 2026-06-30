"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Loader2, Users, ShieldCheck, LayoutGrid, Settings } from "lucide-react";

// Sidebar navigation. `Leads` is live today; the rest are placeholders that mark
// where future admin tools slot in (kept visible-but-disabled so the shell reads
// as an extensible console, not a one-page app).
const NAV: {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  disabled?: boolean;
}[] = [
  { href: "/leads", label: "Leads", icon: Users },
  { href: "#", label: "Boards", icon: LayoutGrid, disabled: true },
  { href: "#", label: "Settings", icon: Settings, disabled: true },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { token, user, isLoading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Client-side guard. This is UX only — admin_service's current_superuser is the
  // real gate on every data call. We just avoid rendering the shell for anyone
  // who isn't a verified superuser session.
  useEffect(() => {
    if (!isLoading && !token) router.replace("/login");
  }, [isLoading, token, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-foreground/70" />
      </div>
    );
  }

  if (!token) return null;

  return (
    <div className="flex min-h-screen bg-background">
      {/* ---- Sidebar ---- */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/40 p-4 md:flex">
        <div className="mb-8 flex items-center gap-2.5 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-foreground text-background">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-bold tracking-tight">SnapRise</div>
            <div className="text-xs text-foreground/50">Backoffice</div>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map((item) => {
            const active = !item.disabled && pathname.startsWith(item.href);
            const Icon = item.icon;
            const className = cn(
              "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
              active
                ? "bg-foreground text-background"
                : "text-foreground/60 hover:bg-input hover:text-foreground",
              item.disabled && "pointer-events-none opacity-40"
            );
            const content = (
              <>
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
                {item.disabled && (
                  <span className="ml-auto text-[10px] uppercase tracking-wide">soon</span>
                )}
              </>
            );
            return item.disabled ? (
              <div key={item.label} className={className}>
                {content}
              </div>
            ) : (
              <Link key={item.label} href={item.href} className={className}>
                {content}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* ---- Main column ---- */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-border bg-background/80 px-6 py-4 backdrop-blur-md">
          <span className="text-sm font-semibold tracking-tight md:hidden">SnapRise Backoffice</span>
          <div className="ml-auto flex items-center gap-4">
            <span className="hidden text-sm text-foreground/60 sm:inline">{user?.email}</span>
            <Button variant="outline" onClick={logout}>
              Logout
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6 sm:p-8">{children}</main>
      </div>
    </div>
  );
}
