"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { otpApi, authApi } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleSendOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // 0. Check if user exists
      const { exists } = await authApi.checkEmail(email);
      if (!exists) {
        setError("No account found for this email address.");
        setIsLoading(false);
        return;
      }

      const result = await otpApi.send(email, "email_verification");
      let otpVerifyUrl = `/otp-verify?email=${encodeURIComponent(email)}&purpose=email_verification&mode=forgot_password`;
      if (result.dev_otp) {
        otpVerifyUrl += `&dev_otp=${result.dev_otp}`;
      }
      router.push(otpVerifyUrl);
    } catch (err: any) {
      setError(err.message || "Failed to send OTP. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Reset Password</h1>
          <p className="text-sm text-muted-foreground">
            Enter your email and we&apos;ll send you an OTP to reset your password
          </p>
        </div>
        
        <form className="space-y-4" onSubmit={handleSendOtp}>
          {error && (
            <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg border border-red-100 text-center">
              {error}
            </div>
          )}
          
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="email">
              Email
            </label>
            <Input 
              id="email" 
              placeholder="name@example.com" 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          
          <Button className="w-full" type="submit" disabled={isLoading}>
            {isLoading ? "Sending OTP..." : "Send OTP"}
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
