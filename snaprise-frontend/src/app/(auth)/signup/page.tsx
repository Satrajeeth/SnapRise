"use client";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";
import Link from "next/link";
import { motion } from "framer-motion";

export default function SignupPage() {
  return (
    <Card className="w-full">
      <div className="space-y-6">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold tracking-tighter">Create an account</h1>
          <p className="text-sm text-muted-foreground">
            Enter your details to get started with SnapRise
          </p>
        </div>
        
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="name">
              Full Name
            </label>
            <Input id="name" placeholder="John Doe" type="text" required />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="email">
              Email
            </label>
            <Input id="email" placeholder="name@example.com" type="email" required />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium leading-none" htmlFor="password">
              Password
            </label>
            <Input id="password" type="password" required />
          </div>
          
          <Button className="w-full" type="submit">
            Sign Up
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
