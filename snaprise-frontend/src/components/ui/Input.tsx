"use client";

import { motion, HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

const Input = forwardRef<HTMLInputElement, HTMLMotionProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <motion.input
        type={type}
        whileFocus={{ scale: 1.01 }}
        className={cn(
          "flex h-11 w-full rounded-xl border border-border bg-input px-4 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 transition-all",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";

export { Input };
