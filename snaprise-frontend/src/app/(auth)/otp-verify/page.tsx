"use client";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { motion } from "framer-motion";
import { useState, useRef, useEffect } from "react";

export default function OtpVerifyPage() {
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleChange = (index: number, value: string) => {
    if (value.length > 1) value = value.slice(-1);
    if (!/^\d*$/.test(value)) return;

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Move to next input if value is entered
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Verify OTP</h1>
          <p className="text-sm text-muted-foreground">
            Enter the 6-digit code sent to your email
          </p>
        </div>
        
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
              className="w-12 h-14 text-center text-2xl font-bold rounded-xl border border-border bg-input focus:ring-2 focus:ring-ring focus:outline-none transition-all"
              whileFocus={{ scale: 1.05 }}
            />
          ))}
        </div>
        
        <Button className="w-full" type="button">
          Verify
        </Button>
        
        <div className="text-center text-sm text-muted-foreground">
          Didn&apos;t receive the code?{" "}
          <button className="text-foreground hover:underline underline-offset-4 transition-colors">
            Resend
          </button>
        </div>
      </div>
    </Card>
  );
}
