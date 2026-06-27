"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { PRICING_TIERS, ROUTES } from "@/constants";
import { cn } from "@/lib/utils";

export default function PricingPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Pricing</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Simple, transparent pricing. Start free and scale as you grow.
        </p>
      </motion.div>

      <div className="mt-16 grid gap-8 pt-4 lg:grid-cols-3">
        {PRICING_TIERS.map((tier, i) => (
          <motion.div
            key={tier.id}
            className="relative"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            {"popular" in tier && tier.popular && (
              <div className="absolute -top-3 left-1/2 z-10 -translate-x-1/2 rounded-full bg-teal-500 px-3 py-1 text-xs font-medium text-white shadow-sm">
                Most Popular
              </div>
            )}
            <Card
              className={cn(
                "h-full flex flex-col",
                "popular" in tier && tier.popular && "border-teal-500/50 ring-1 ring-teal-500/20"
              )}
            >
              <CardHeader>
                <CardTitle className="text-xl">{tier.name}</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">
                    {tier.price === 0 ? "Free" : `$${tier.price}`}
                  </span>
                  {tier.price > 0 && (
                    <span className="text-muted-foreground">/month</span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex-1">
                <ul className="space-y-3">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm">
                      <Check className="mt-0.5 size-4 shrink-0 text-teal-400" />
                      {feature}
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  variant={"popular" in tier && tier.popular ? "default" : "outline"}
                  asChild
                >
                  <Link href={ROUTES.REGISTER}>
                    {tier.price === 0 ? "Get Started" : "Upgrade"}
                  </Link>
                </Button>
              </CardFooter>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
