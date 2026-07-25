"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ImagePlus,
  Video,
  Briefcase,
  CreditCard,
  Settings,
  LogOut,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { PORTAL_NAV_ITEMS, ROUTES } from "@/constants";
import { cn } from "@/lib/utils";

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  LayoutDashboard,
  ImagePlus,
  Video,
  Briefcase,
  CreditCard,
  Settings,
};

export function PortalSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 flex-col border-r border-border/50 bg-sidebar">
      <div className="flex h-16 items-center px-5">
        <Logo size="sm" />
      </div>

      <Separator />

      <nav className="flex-1 space-y-1 p-3">
        {PORTAL_NAV_ITEMS.map((item) => {
          const Icon = iconMap[item.icon];
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-foreground"
              )}
            >
              {Icon && <Icon className="size-4 shrink-0" />}
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border/50 p-3">
        <div className="mb-2 flex items-center justify-between px-2">
          <span className="text-xs text-muted-foreground">Theme</span>
          <ThemeToggle />
        </div>
        <Button variant="ghost" size="sm" className="w-full justify-start gap-3 text-muted-foreground" asChild>
          <Link href={ROUTES.HOME}>
            <LogOut className="size-4" />
            Exit Portal
          </Link>
        </Button>
      </div>
    </aside>
  );
}
