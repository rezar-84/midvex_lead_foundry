import { LogOut } from "lucide-react"
import { NavLink, Outlet } from "react-router"

import { useMe } from "@/api/queries"
import type { Capability } from "@/api/types"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

interface NavItem {
  to: string
  label: string
  capability: Capability
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Overview", capability: "view" },
  { to: "/projects", label: "Projects", capability: "view" },
  { to: "/opportunities", label: "Opportunities", capability: "view" },
  { to: "/conversations", label: "Conversations", capability: "view" },
  { to: "/knowledge", label: "Knowledge", capability: "view" },
  { to: "/sources", label: "Sources", capability: "manage_sources" },
  { to: "/settings", label: "Settings", capability: "manage_users" },
]

function cookie(name: string): string {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : ""
}

function LogoutForm() {
  return (
    <form method="post" action="/accounts/logout/">
      <input type="hidden" name="csrfmiddlewaretoken" value={cookie("csrftoken")} />
      <Button type="submit" variant="ghost" size="sm" className="gap-1.5">
        <LogOut className="size-4" aria-hidden />
        Sign out
      </Button>
    </form>
  )
}

export function AppShell() {
  const { data: me, isPending } = useMe()

  return (
    <div className="min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-card focus:px-3 focus:py-2 focus:shadow"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-border bg-card/85 backdrop-blur">
        <div className="mx-auto flex min-h-[64px] w-full max-w-[1180px] items-center gap-8 px-5">
          <NavLink to="/" className="text-sm font-black tracking-[0.08em] uppercase">
            {isPending ? <Skeleton className="h-4 w-28" /> : (me?.brand_name || "Lead Foundry")}
          </NavLink>
          <nav aria-label="Primary" className="flex flex-1 items-center gap-1 overflow-x-auto">
            {NAV_ITEMS.filter(
              (item) => me?.capabilities.includes(item.capability) ?? false,
            ).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
                    isActive && "bg-accent font-medium text-accent-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          {me ? (
            <div className="flex items-center gap-3">
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {me.username} · {me.role}
              </span>
              <LogoutForm />
            </div>
          ) : null}
        </div>
      </header>
      <main id="main-content" className="mx-auto w-full max-w-[1180px] px-5 py-10">
        <Outlet />
      </main>
    </div>
  )
}
