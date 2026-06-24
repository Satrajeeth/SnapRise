"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { otpApi, authApi } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Eye, EyeOff } from "lucide-react";

export default function SignupPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const { token } = useAuth();

  useEffect(() => {
    if (token) {
      router.push("/dashboard");
    }
  }, [token, router]);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      // 0. Check if user already exists
      const { exists } = await authApi.checkEmail(email);
      if (exists) {
        setError("An account with this email already exists. Please login.");
        setIsLoading(false);
        return;
      }

      // 1. Send OTP
      const result = await otpApi.send(email, "email_verification");
      
      // 2. Store signup info temporarily in sessionStorage for completion after OTP
      sessionStorage.setItem("signup_data", JSON.stringify({ name, email, password }));
      
      // 3. Redirect to OTP verification
      let otpVerifyUrl = `/otp-verify?email=${encodeURIComponent(email)}&purpose=email_verification&mode=signup`;
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
          <h1 className="text-3xl font-bold tracking-tighter">Create an account</h1>
          <p className="text-sm text-muted-foreground">
            Enter your details to get started with SnapRise
          </p>
        </div>
        
        <form className="space-y-4" onSubmit={handleSignup}>
          {error && (
            <div className="p-3 text-sm text-red-500 bg-red-50 rounded-lg border border-red-100 text-center">
              {error}
            </div>
          )}
          
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="name">
              Full Name
            </label>
            <Input 
              id="name" 
              placeholder="John Doe" 
              type="text" 
              required 
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

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
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          
          <Button className="w-full" type="submit" disabled={isLoading}>
            {isLoading ? "Sending OTP..." : "Sign Up"}
          </Button>
        </form>
        
        <div className="text-center text-sm">
          Already have an account?{" "}
          <Link href="/login" className="underline underline-offset-4 hover:text-primary transition-colors">
            Login
          </Link>
        </div>
      </div>
    </Card>
  );
}
