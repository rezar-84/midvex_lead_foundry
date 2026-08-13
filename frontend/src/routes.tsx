import { createBrowserRouter } from "react-router"

import { AppShell } from "@/components/AppShell"
import { ConversationsPage } from "@/pages/Conversations"
import { DashboardPage } from "@/pages/Dashboard"
import { KnowledgePage } from "@/pages/Knowledge"
import { OpportunitiesPage } from "@/pages/Opportunities"
import { OpportunityDetailPage } from "@/pages/OpportunityDetail"
import { Placeholder } from "@/pages/Placeholder"

// Route paths deliberately mirror the legacy Django URLs so bookmarks keep working.
// While a legacy template page still exists, Django serves it and the SPA never
// sees that path; each page replaces its placeholder as it is rebuilt.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "projects/*", element: <Placeholder title="Projects" /> },
      { path: "opportunities", element: <OpportunitiesPage /> },
      { path: "opportunities/:candidateId", element: <OpportunityDetailPage /> },
      { path: "conversations", element: <ConversationsPage /> },
      { path: "knowledge", element: <KnowledgePage /> },
      { path: "sources", element: <Placeholder title="Sources" /> },
      { path: "settings", element: <Placeholder title="Settings" /> },
      { path: "*", element: <Placeholder title="Not found" /> },
    ],
  },
])
