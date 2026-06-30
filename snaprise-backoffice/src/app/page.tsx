"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { Loader2 } from "lucide-react";

// Entry point: bounce to the leads console if signed in, otherwise to login.
// The real authorization happens in the (admin) layout + admin_service; this is
// just a convenience redirect.
export default function Home() {
  const { token, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    router.replace(token ? "/leads" : "/login");
  }, [token, isLoading, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Loader2 className="h-10 w-10 animate-spin text-foreground/70" />
    </div>
  );
}
