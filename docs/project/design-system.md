---
status: draft
owner: brand-designer
last-reviewed: 2026-08-13
---

# Design system — Midvex Lead Foundry

The authoritative tokens live in `frontend/src/index.css` (Tailwind 4 theme feeding shadcn/ui components); the legacy `app.css` retains only what the surviving login/MFA templates need. The interface is a restrained, dense internal workspace on the warm paper-and-green palette, rendered in a soft-UI (neumorphic) style: surfaces share the page ground and read as raised or inset through the `.neu-raised` / `.neu-flat` / `.neu-inset` dual-shadow utilities, with matching light and dark palettes. Geist Variable is bundled locally (no third-party font requests) and covers Turkish and English.

Components: skip link, navigation, status badge, metric card, filter form, data table, timeline, evidence block, pagination, confirmation form and inline error. Each implements focus, disabled, loading, error and long-content behavior.

Every view supports empty, loading, partial, error, unauthorised, forbidden, not-found, success and extreme-content states. Layout reflows from a single-column small viewport to the desktop review workspace; no horizontal two-dimensional navigation is required for primary tasks.

Target WCAG 2.2 AA. All pointer actions are keyboard actions; focus is visible; colour is never the only status signal; primary controls target 44×44 CSS pixels. Screen-reader/browser pairs are not yet verified and no conformance claim may be published.
