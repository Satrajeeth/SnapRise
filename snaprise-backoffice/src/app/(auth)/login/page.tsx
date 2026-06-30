"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import { useState, useEffect } from "react";
import { authApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, token, authError } = useAuth();
  const router = useRouter();

  // Already a (verified superuser) session → go straight to the console.
  useEffect(() => {
    if (token) router.push("/leads");
  }, [token, router]);

  // The superuser gate runs asynchronously after login(); if it refuses the
  // account, authError is set — re-enable the form so they can switch accounts.
  useEffect(() => {
    if (authError) setSubmitting(false);
  }, [authError]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await authApi.login(email, password);
      // login() verifies the token, enforces the superuser gate, and (on
      // success) redirects to /leads. We keep `submitting` true through that
      // async step; a refusal flips it back via the authError effect above.
      login(response.access_token, response.refresh_token);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Sign in failed";
      setError(
        message === "LOGIN_BAD_CREDENTIALS" ? "Invalid email or password" : message
      );
      setSubmitting(false);
    }
  };

  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Backoffice</h1>
          <p className="text-sm text-foreground/50">
            Sign in with an administrator account
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleLogin}>
          {(error || authError) && (
            <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg border border-red-100 text-center dark:bg-red-500/10 dark:border-red-500/20">
              {error || authError}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              placeholder="admin@example.com"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-foreground/50 hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <Button className="w-full" type="submit" disabled={submitting}>
            {submitting ? "Signing In..." : "Sign In"}
          </Button>
        </form>
      </div>
    </Card>
  );
}
