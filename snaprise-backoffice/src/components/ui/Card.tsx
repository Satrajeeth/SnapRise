"use client";

import { motion, HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";
import { cn } from "@/lib/utils";

const Card = forwardRef<HTMLDivElement, HTMLMotionProps<"div">>(
  ({ className, ...props }, ref) => (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={cn("glass rounded-2xl p-8 shadow-2xl shadow-black/5", className)}
      {...props}
    />
  )
);

Card.displayName = "Card";

export { Card };
