import Image from "next/image";
import Link from "next/link";
import { APP_NAME } from "@/constants";
import { cn } from "@/lib/utils";

interface LogoProps {
  className?: string;
  showText?: boolean;
  size?: "sm" | "md" | "lg";
}

const sizes = {
  sm: { img: 28, text: "text-base" },
  md: { img: 36, text: "text-lg" },
  lg: { img: 48, text: "text-xl" },
};

export function Logo({ className, showText = true, size = "md" }: LogoProps) {
  const s = sizes[size];

  return (
    <Link
      href="/"
      className={cn("flex items-center gap-2.5 font-semibold tracking-tight", className)}
    >
      <Image
        src="/logo.svg"
        alt={APP_NAME}
        width={s.img}
        height={s.img}
        className="rounded-md"
        priority
      />
      {showText && (
        <span className={cn(s.text, "bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text")}>
          {APP_NAME}
        </span>
      )}
    </Link>
  );
}
