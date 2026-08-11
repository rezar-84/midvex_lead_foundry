---
status: draft
owner: brand-designer
last-reviewed: 2026-08-11
---

# Design system — Midvex Lead Foundry

The authoritative tokens live in `foundry/static/foundry/app.css`. The interface is a restrained, dense internal workspace: neutral surfaces, one action accent, and separate success/warning/danger semantics. System fonts support Turkish and English without third-party font requests.

Components: skip link, navigation, status badge, metric card, filter form, data table, timeline, evidence block, pagination, confirmation form and inline error. Each implements focus, disabled, loading, error and long-content behavior.

Every view supports empty, loading, partial, error, unauthorised, forbidden, not-found, success and extreme-content states. Layout reflows from a single-column small viewport to the desktop review workspace; no horizontal two-dimensional navigation is required for primary tasks.

Target WCAG 2.2 AA. All pointer actions are keyboard actions; focus is visible; colour is never the only status signal; primary controls target 44×44 CSS pixels. Screen-reader/browser pairs are not yet verified and no conformance claim may be published.
