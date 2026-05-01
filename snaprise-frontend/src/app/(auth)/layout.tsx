"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-background flex flex-col items-center justify-center p-4">
      {/* Subtle background animation */}
      <div className="absolute inset-0 z-0">
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut",
          }}
          className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] rounded-full bg-foreground/5 blur-[120px]"
        />
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2,
          }}
          className="absolute -bottom-[10%] -right-[10%] w-[50%] h-[50%] rounded-full bg-foreground/5 blur-[120px]"
        />
      </div>

      <div className="relative z-10 w-full max-w-md flex flex-col items-center">
        <Link href="/" className="mb-8">
          <motion.div
            whileHover={{ scale: 1.05, rotate: [0, -5, 5, 0] }}
            whileTap={{ scale: 0.95 }}
            className="w-20 h-20 relative"
          >
            <Image
              src="/logo.jpeg"
              alt="SnapRise Logo"
              fill
              className="object-contain rounded-2xl grayscale invert"
            />
          </motion.div>
        </Link>
        
        {children}
      </div>
    </div>
  );
}
