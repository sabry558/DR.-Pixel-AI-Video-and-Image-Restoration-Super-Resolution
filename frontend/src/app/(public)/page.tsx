"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  Upload,
  Cpu,
  Download,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { BeforeAfterSlider } from "@/components/marketing/before-after-slider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FEATURES, ROUTES } from "@/constants";

const steps = [
  { icon: Upload, title: "Upload Media", description: "Drag and drop your damaged photos or videos." },
  { icon: Cpu, title: "AI Processing", description: "Our models analyze and restore every detail." },
  { icon: Download, title: "Download Results", description: "Get your enhanced media in stunning quality." },
];

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.5 },
};

export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="hero-glow absolute inset-0" />
        <div className="grid-pattern absolute inset-0 opacity-50" />
        <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8">
          <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
            >
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-500/20 bg-teal-500/10 px-4 py-1.5 text-sm text-teal-400">
                <Sparkles className="size-3.5" />
                AI-Powered Restoration
              </div>
              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
                Restore Every Pixel.
                <br />
                <span className="gradient-text">Revive Every Memory.</span>
              </h1>
              <p className="mt-6 max-w-lg text-lg text-muted-foreground">
                AI-powered image and video restoration for damaged, blurry, noisy, and low-quality media.
              </p>
              <div className="mt-8 flex flex-wrap gap-4">
                <Button size="lg" asChild>
                  <Link href={ROUTES.REGISTER}>
                    Get Started
                    <ArrowRight className="ml-1 size-4" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild>
                  <Link href={ROUTES.SHOWCASE}>View Showcase</Link>
                </Button>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <BeforeAfterSlider />
            </motion.div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/50 bg-muted/20 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div className="text-center" {...fadeUp}>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Professional-grade restoration
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-muted-foreground">
              State-of-the-art AI models trained to recover detail, color, and clarity from even the most degraded media.
            </p>
          </motion.div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.id}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.08 }}
              >
                <Card className="h-full border-border/50 bg-card/50 backdrop-blur-sm transition-colors hover:border-teal-500/30">
                  <CardContent className="p-6">
                    <div className="mb-4 flex size-10 items-center justify-center rounded-lg bg-teal-500/10 text-teal-400">
                      <Sparkles className="size-5" />
                    </div>
                    <h3 className="text-lg font-semibold">{feature.title}</h3>
                    <p className="mt-2 text-sm text-muted-foreground">{feature.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div className="text-center" {...fadeUp}>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">How it works</h2>
            <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
              Three simple steps to bring your memories back to life.
            </p>
          </motion.div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {steps.map((step, i) => (
              <motion.div
                key={step.title}
                className="relative text-center"
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.15 }}
              >
                <div className="mx-auto mb-6 flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-cyan-500/10 ring-1 ring-teal-500/20">
                  <step.icon className="size-6 text-teal-400" />
                </div>
                <div className="mb-2 text-sm font-medium text-teal-400">Step {i + 1}</div>
                <h3 className="text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-border/50 py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <motion.div
            className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-teal-600/20 via-background to-cyan-600/10 px-8 py-16 text-center ring-1 ring-teal-500/20 sm:px-16"
            {...fadeUp}
          >
            <div className="hero-glow absolute inset-0" />
            <div className="relative">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Ready to restore your memories?
              </h2>
              <p className="mx-auto mt-4 max-w-lg text-muted-foreground">
                Create a free account and start restoring your first 5 images this month — no credit card required.
              </p>
              <Button size="lg" className="mt-8" asChild>
                <Link href={ROUTES.REGISTER}>
                  Create Free Account
                  <ArrowRight className="ml-1 size-4" />
                </Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>
    </>
  );
}
