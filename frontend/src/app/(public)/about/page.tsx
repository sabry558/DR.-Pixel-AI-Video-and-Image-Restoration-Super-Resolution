"use client";

import Image from "next/image";
import { motion } from "framer-motion";
import { Heart, Target, Zap } from "lucide-react";
import { APP_DESCRIPTION, APP_NAME } from "@/constants";

const values = [
  {
    icon: Heart,
    title: "Preserve Memories",
    description: "Every photograph and video holds irreplaceable moments. We help you keep them alive.",
  },
  {
    icon: Target,
    title: "Precision Restoration",
    description: "Our AI models are trained to recover detail without introducing artifacts or distortion.",
  },
  {
    icon: Zap,
    title: "Accessible Technology",
    description: "Professional-grade restoration tools, available to everyone — from families to studios.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <div className="mx-auto mb-8 flex justify-center">
          <Image
            src="/logo.svg"
            alt={APP_NAME}
            width={120}
            height={120}
            className="rounded-2xl"
          />
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">About {APP_NAME}</h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground">
          {APP_DESCRIPTION}
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mx-auto mt-16 max-w-3xl space-y-6 text-center text-muted-foreground"
      >
        <p className="text-lg leading-relaxed">
          Dr. Pixel was founded with a simple mission: using AI to restore memories and improve visual quality.
          Whether it&apos;s a faded family photograph from decades ago or degraded VHS footage, we believe
          everyone deserves access to tools that can bring their media back to life.
        </p>
        <p className="leading-relaxed">
          Our team combines deep expertise in computer vision, machine learning, and user experience to
          deliver restoration results that were once only possible in professional studios — now available
          to anyone with an internet connection.
        </p>
      </motion.div>

      <div className="mt-20 grid gap-8 md:grid-cols-3">
        {values.map((value, i) => (
          <motion.div
            key={value.title}
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.1 }}
            className="rounded-2xl border border-border/50 bg-card/50 p-8 text-center"
          >
            <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-xl bg-teal-500/10 text-teal-400">
              <value.icon className="size-6" />
            </div>
            <h3 className="text-lg font-semibold">{value.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{value.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
