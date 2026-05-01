"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { motion } from "framer-motion";

export default function LoginPage() {
  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Welcome back</h1>
          <p className="text-sm text-muted-foreground">
            Enter your credentials to access your account
          </p>
        </div>
        
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="email">
              Email
            </label>
            <Input id="email" placeholder="name@example.com" type="email" required />
          </div>
          
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium leading-none" htmlFor="password">
                Password
              </label>
              <Link
                href="/forgot-password"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                Forgot password?
              </Link>
            </div>
            <Input id="password" type="password" required />
          </div>
          
          <Button className="w-full" type="submit">
            Sign In
          </Button>
        </form>
        
        <div className="text-center text-sm">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="underline underline-offset-4 hover:text-primary transition-colors">
            Sign up
          </Link>
        </div>
      </div>
    </Card>
  );
}
