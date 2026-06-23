"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { motion } from "framer-motion";
import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { otpApi, authApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

function OtpVerifyContent() {
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [resetToken, setResetToken] = useState<string | null>(null);
  const [newPassword, setNewPassword] = useState("");
  
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login } = useAuth();
  
  const email = searchParams.get("email") || "";
  const purpose = searchParams.get("purpose") || "email_verification";
  const mode = searchParams.get("mode") || "signup";
  const devOtp = searchParams.get("dev_otp");

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = (index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1);
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleVerify = async () => {
    const code = otp.join("");
    if (code.length !== 6) {
      setError("Please enter a 6-digit code");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const { proof_token } = await otpApi.verify(email, purpose, code);
      
      if (mode === "signup") {
        const signupData = JSON.parse(sessionStorage.getItem("signup_data") || "{}");
        try {
          await authApi.register(
            {
              email: signupData.email,
              password: signupData.password,
              is_active: true,
              is_superuser: false,
              is_verified: true,
            },
            proof_token
          );
          
          // Auto login
          const loginResponse = await authApi.login(signupData.email, signupData.password);
          sessionStorage.removeItem("signup_data");
          login(loginResponse.access_token);
        } catch (err: any) {
          if (err.message === "REGISTER_USER_ALREADY_EXISTS") {
            setError("An account with this email already exists. Please login.");
          } else {
            throw err;
          }
        }
      } else if (mode === "forgot_password") {
        const { token } = await authApi.forgotPassword(email, proof_token);
        if (!token) {
          setError("No account found for this email address.");
        } else {
          setResetToken(token);
          setIsVerified(true);
        }
      }
    } catch (err: any) {
      setError(err.message || "Verification failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetToken) return;

    setIsLoading(true);
    setError(null);

    try {
      await authApi.resetPassword(resetToken, newPassword);
      router.push("/login?message=Password reset successful");
    } catch (err: any) {
      setError(err.message || "Failed to reset password");
    } finally {
      setIsLoading(false);
    }
  };

  if (isVerified && mode === "forgot_password") {
    return (
      <Card className="w-full">
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-3xl font-bold tracking-tighter">New Password</h1>
            <p className="text-sm text-muted-foreground">
              Enter your new password below
            </p>
          </div>
          
          <form className="space-y-4" onSubmit={handleResetPassword}>
            {error && (
              <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg border border-red-100 text-center">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium leading-none" htmlFor="password">
                Password
              </label>
              <Input 
                id="password" 
                type="password" 
                required 
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
            </div>
            <Button className="w-full" type="submit" disabled={isLoading}>
              {isLoading ? "Resetting..." : "Reset Password"}
            </Button>
          </form>
        </div>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Verify OTP</h1>
          <p className="text-sm text-muted-foreground">
            Enter the 6-digit code sent to {email}
          </p>
        </div>
        
        {devOtp && (
          <div className="p-3 text-sm bg-amber-50 border border-amber-200 rounded-lg text-center">
            <span className="font-semibold text-amber-800">🔧 Dev Mode</span>
            <span className="text-amber-700"> — Your OTP is: </span>
            <span className="font-mono font-bold text-amber-900 text-lg">{devOtp}</span>
          </div>
        )}

        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg border border-red-100 text-center">
            {error}
          </div>
        )}

        <div className="flex justify-between gap-2">
          {otp.map((digit, index) => (
            <motion.input
              key={index}
              ref={(el) => {
                inputRefs.current[index] = el;
              }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(index, e.target.value)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              className="w-10 h-12 sm:w-12 sm:h-14 text-center text-2xl font-bold rounded-xl border border-border bg-input focus:ring-2 focus:ring-ring focus:outline-none transition-all"
              whileFocus={{ scale: 1.05 }}
            />
          ))}
        </div>
        
        <Button className="w-full" type="button" onClick={handleVerify} disabled={isLoading}>
          {isLoading ? "Verifying..." : "Verify"}
        </Button>
        
        <div className="text-center text-sm text-muted-foreground">
          Didn&apos;t receive the code?{" "}
          <button 
            className="text-foreground hover:underline underline-offset-4 transition-colors disabled:opacity-50"
            onClick={() => otpApi.send(email, purpose)}
            disabled={isLoading}
          >
            Resend
          </button>
        </div>
      </div>
    </Card>
  );
}

export default function OtpVerifyPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <OtpVerifyContent />
    </Suspense>
  );
}
