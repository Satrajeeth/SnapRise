"use client";

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { boardApi } from "@/lib/api/boards";
import { Loader2, CheckCircle2, XCircle, Mail } from "lucide-react";
import { Button } from "@/components/ui/Button";

// The accept link from the invitation email points here:
//   {FRONTEND_BASE_URL}/invite/{token}
// The `token` is the raw invite secret (not a JWT). This page exchanges it for a
// real board membership once the visitor is authenticated.

type State =
  | { kind: "loading" }
  | { kind: "needs-auth" }
  | { kind: "accepting" }
  | { kind: "accepted"; boardId: string }
  | { kind: "error"; message: string };

const POST_LOGIN_REDIRECT_KEY = "post_login_redirect";

export default function InviteAcceptPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token: inviteToken } = use(params);
  const { token, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "loading" });
  // Guard so the one-shot accept POST never fires twice (e.g. StrictMode / re-render).
  const attempted = useRef(false);

  useEffect(() => {
    if (authLoading) return;

    if (!token) {
      // Not logged in: remember to return here, then prompt for login/signup.
      // AuthContext.login() consumes this key after a successful sign-in.
      localStorage.setItem(POST_LOGIN_REDIRECT_KEY, `/invite/${inviteToken}`);
      setState({ kind: "needs-auth" });
      return;
    }

    if (attempted.current) return;
    attempted.current = true;

    setState({ kind: "accepting" });
    boardApi
      .acceptInvitation(token, inviteToken)
      .then((res) => {
        setState({ kind: "accepted", boardId: res.board_id });
        // Let the success state show briefly, then drop them into the board.
        setTimeout(() => router.push(`/dashboard/boards/${res.board_id}`), 1200);
      })
      .catch((err) => {
        setState({
          kind: "error",
          message: err instanceof Error ? err.message : "Could not accept this invitation",
        });
      });
  }, [authLoading, token, inviteToken, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 text-center">
        {(state.kind === "loading" || state.kind === "accepting") && (
          <>
            <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-foreground/70" />
            <h1 className="text-lg font-semibold">
              {state.kind === "accepting" ? "Accepting your invitation…" : "Loading…"}
            </h1>
          </>
        )}

        {state.kind === "needs-auth" && (
          <>
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-purple-100 text-[#9333EA]">
              <Mail className="h-6 w-6" />
            </div>
            <h1 className="mb-1 text-lg font-semibold">You&apos;ve been invited to a board</h1>
            <p className="mb-6 text-sm text-foreground/50">
              Log in or create an account to accept your invitation. We&apos;ll bring you right back.
            </p>
            <div className="flex items-center justify-center gap-3">
              <Link href="/login">
                <Button>Log in</Button>
              </Link>
              <Link href="/signup">
                <Button variant="outline">Sign up</Button>
              </Link>
            </div>
          </>
        )}

        {state.kind === "accepted" && (
          <>
            <CheckCircle2 className="mx-auto mb-4 h-10 w-10 text-emerald-500" />
            <h1 className="mb-1 text-lg font-semibold">You&apos;re in!</h1>
            <p className="text-sm text-foreground/50">Taking you to the board…</p>
          </>
        )}

        {state.kind === "error" && (
          <>
            <XCircle className="mx-auto mb-4 h-10 w-10 text-red-500" />
            <h1 className="mb-1 text-lg font-semibold">Invitation unavailable</h1>
            <p className="mb-6 text-sm text-foreground/50">{state.message}</p>
            <Link href="/dashboard">
              <Button variant="outline">Go to dashboard</Button>
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
