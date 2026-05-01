"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function ForgotPasswordPage() {
  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Reset Password</h1>
          <p className="text-sm text-muted-foreground">
            Enter your email and we&apos;ll send you a link to reset your password
          </p>
        </div>
        
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="email">
              Email
            </label>
            <Input id="email" placeholder="name@example.com" type="email" required />
          </div>
          
          <Button className="w-full" type="submit">
            Send Reset Link
          </Button>
        </form>
        
        <div className="text-center">
          <Link
            href="/login"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to login
          </Link>
        </div>
      </div>
    </Card>
  );
}
