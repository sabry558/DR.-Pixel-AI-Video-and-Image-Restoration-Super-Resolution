import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: number;
  icon: React.ComponentType<{ className?: string }>;
  variant?: "default" | "success" | "warning" | "danger";
}

const variants = {
  default: "text-foreground",
  success: "text-teal-400",
  warning: "text-amber-400",
  danger: "text-red-400",
};

export function StatCard({ title, value, icon: Icon, variant = "default" }: StatCardProps) {
  return (
    <Card className="border-border/50">
      <CardContent className="flex items-center gap-4 p-6">
        <div className={cn("flex size-12 items-center justify-center rounded-xl bg-muted", variants[variant])}>
          <Icon className="size-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}
