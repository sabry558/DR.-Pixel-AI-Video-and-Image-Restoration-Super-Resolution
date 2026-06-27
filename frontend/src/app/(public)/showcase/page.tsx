"use client";

import { motion } from "framer-motion";
import { BeforeAfterSlider } from "@/components/marketing/before-after-slider";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { SHOWCASE_ITEMS } from "@/constants";

const improvements: Record<string, string[]> = {
  vhs: ["Color correction", "Noise reduction", "Sharpness enhancement"],
  photo: ["Scratch removal", "Detail recovery", "Color restoration"],
  "night-video": ["Brightness boost", "Noise removal", "Detail enhancement"],
  historical: ["Film grain reduction", "Color grading", "Resolution upscaling"],
};

export default function ShowcasePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">Showcase</h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          See the transformative power of AI restoration. Drag the slider to compare before and after.
        </p>
      </motion.div>

      <div className="mt-16 space-y-16">
        {SHOWCASE_ITEMS.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 32 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="overflow-hidden border-border/50">
              <div className="grid lg:grid-cols-2">
                <div className="p-6 lg:p-8">
                  <Badge variant="secondary" className="mb-4 capitalize">
                    {item.category.replace("-", " ")}
                  </Badge>
                  <h2 className="text-2xl font-bold">{item.title}</h2>
                  <p className="mt-3 text-muted-foreground">{item.description}</p>
                  <div className="mt-6">
                    <h3 className="text-sm font-semibold">Improvements</h3>
                    <ul className="mt-3 space-y-2">
                      {(improvements[item.category] ?? []).map((imp) => (
                        <li key={imp} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className="size-1.5 rounded-full bg-teal-400" />
                          {imp}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
                <CardContent className="p-4 lg:p-6">
                  <BeforeAfterSlider />
                </CardContent>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
