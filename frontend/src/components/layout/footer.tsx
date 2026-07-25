import Link from "next/link";
import { Logo } from "@/components/logo";
import { APP_DESCRIPTION, ROUTES } from "@/constants";

const footerLinks = {
  Product: [
    { label: "Solutions", href: ROUTES.SOLUTIONS },
    { label: "Showcase", href: ROUTES.SHOWCASE },
    { label: "Pricing", href: ROUTES.PRICING },
  ],
  Company: [{ label: "About", href: ROUTES.ABOUT }],
  Resources: [{ label: "API Documentation", href: "#" }],
  Legal: [
    { label: "Privacy Policy", href: "#" },
    { label: "Terms of Service", href: "#" },
  ],
};

export function Footer() {
  return (
    <footer className="border-t border-border/50 bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-12 md:grid-cols-2 lg:grid-cols-6">
          <div className="lg:col-span-2">
            <Logo />
            <p className="mt-4 max-w-xs text-sm text-muted-foreground">
              {APP_DESCRIPTION}
            </p>
          </div>

          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title}>
              <h3 className="text-sm font-semibold">{title}</h3>
              <ul className="mt-4 space-y-3">
                {links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 border-t border-border/50 pt-8 text-center text-sm text-muted-foreground">
          © {new Date().getFullYear()} Dr. Pixel. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
