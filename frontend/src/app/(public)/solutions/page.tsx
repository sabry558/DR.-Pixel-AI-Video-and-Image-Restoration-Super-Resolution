"use client";

import { motion } from "framer-motion";
import { ImageIcon, Video, Building2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SOLUTIONS } from "@/constants";

const icons = [ImageIcon, Video, Building2];

export default function SolutionsPage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Solutions</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Tailored restoration workflows for every type of media and every use case.
        </p>
      </motion.div>

      <div className="mt-16 grid gap-8 lg:grid-cols-3">
        {SOLUTIONS.map((solution, i) => {
          const Icon = icons[i];
          return (
            <motion.div
              key={solution.id}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className="h-full border-border/50 transition-colors hover:border-teal-500/30">
                <CardHeader>
                  <div className="mb-2 flex size-12 items-center justify-center rounded-xl bg-teal-500/10 text-teal-400">
                    <Icon className="size-6" />
                  </div>
                  <CardTitle className="text-xl">{solution.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{solution.description}</p>
                  <ul className="mt-6 space-y-2">
                    {solution.examples.map((example) => (
                      <li key={example} className="flex items-center gap-2 text-sm">
                        <span className="size-1.5 rounded-full bg-teal-400" />
                        {example}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
