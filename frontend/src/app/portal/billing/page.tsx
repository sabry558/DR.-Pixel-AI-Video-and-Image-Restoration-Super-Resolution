"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { PRICING_TIERS, ROUTES } from "@/constants";
import { MOCK_USAGE } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export default function BillingPage() {
  const usagePercent = (MOCK_USAGE.jobsUsed / MOCK_USAGE.jobsLimit) * 100;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
        <p className="text-muted-foreground">Manage your plan and usage.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Current Plan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">{MOCK_USAGE.plan}</span>
              <span className="text-muted-foreground">$29/month</span>
            </div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <Check className="size-4 text-teal-400" />
                100 jobs per month
              </li>
              <li className="flex items-center gap-2">
                <Check className="size-4 text-teal-400" />
                1080p exports
              </li>
              <li className="flex items-center gap-2">
                <Check className="size-4 text-teal-400" />
                Priority queue
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Monthly Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Jobs used</span>
              <span className="font-semibold">
                {MOCK_USAGE.jobsUsed} / {MOCK_USAGE.jobsLimit}
              </span>
            </div>
            <Progress value={usagePercent} className="h-2" />
            <p className="text-xs text-muted-foreground">
              {MOCK_USAGE.jobsLimit - MOCK_USAGE.jobsUsed} jobs remaining · {MOCK_USAGE.period}
            </p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="mb-4 text-lg font-semibold">Upgrade Options</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {PRICING_TIERS.map((tier) => (
            <Card
              key={tier.id}
              className={cn(
                "border-border/50",
                tier.id === "pro" && "border-teal-500/30"
              )}
            >
              <CardContent className="p-6">
                <h3 className="font-semibold">{tier.name}</h3>
                <p className="mt-1 text-2xl font-bold">
                  {tier.price === 0 ? "Free" : `$${tier.price}`}
                  {tier.price > 0 && <span className="text-sm font-normal text-muted-foreground">/mo</span>}
                </p>
                <p className="mt-2 text-sm text-muted-foreground">{tier.jobs}</p>
                <Button
                  variant={tier.id === MOCK_USAGE.plan.toLowerCase() ? "secondary" : "outline"}
                  size="sm"
                  className="mt-4 w-full"
                  disabled={tier.id === MOCK_USAGE.plan.toLowerCase()}
                  asChild={tier.id !== MOCK_USAGE.plan.toLowerCase()}
                >
                  {tier.id === MOCK_USAGE.plan.toLowerCase() ? (
                    <span>Current Plan</span>
                  ) : (
                    <Link href={ROUTES.REGISTER}>Upgrade</Link>
                  )}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
