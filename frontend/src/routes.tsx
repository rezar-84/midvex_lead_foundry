import { createBrowserRouter } from "react-router"

import { AppShell } from "@/components/AppShell"
import { Placeholder } from "@/pages/Placeholder"

// Route paths deliberately mirror the legacy Django URLs so bookmarks keep working.
// While a legacy template page still exists, Django serves it and the SPA never
// sees that path; each page replaces its placeholder as it is rebuilt.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Placeholder title="Overview" /> },
      { path: "projects/*", element: <Placeholder title="Projects" /> },
      { path: "opportunities/*", element: <Placeholder title="Opportunities" /> },
      { path: "conversations", element: <Placeholder title="Conversations" /> },
      { path: "knowledge", element: <Placeholder title="Knowledge" /> },
      { path: "sources", element: <Placeholder title="Sources" /> },
      { path: "settings", element: <Placeholder title="Settings" /> },
      { path: "*", element: <Placeholder title="Not found" /> },
    ],
  },
])
