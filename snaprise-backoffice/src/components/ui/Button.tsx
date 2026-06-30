"use client";

import { motion, HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends HTMLMotionProps<"button"> {
  variant?: "primary" | "secondary" | "outline" | "ghost";
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", ...props }, ref) => {
    const variants = {
      primary: "bg-foreground text-background hover:opacity-90",
      secondary: "bg-input text-foreground hover:bg-border",
      outline: "border border-border bg-transparent hover:bg-input",
      ghost: "bg-transparent hover:bg-input",
    };

    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "inline-flex h-11 items-center justify-center rounded-xl px-6 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";

export { Button };
