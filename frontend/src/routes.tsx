import { createBrowserRouter } from "react-router"

import { AppShell } from "@/components/AppShell"
import { ConversationsPage } from "@/pages/Conversations"
import { DashboardPage } from "@/pages/Dashboard"
import { DataQualityPage } from "@/pages/DataQuality"
import { KnowledgePage } from "@/pages/Knowledge"
import { OpportunitiesPage } from "@/pages/Opportunities"
import { OpportunityDetailPage } from "@/pages/OpportunityDetail"
import { Placeholder } from "@/pages/Placeholder"
import { SettingsPage } from "@/pages/Settings"
import { SourcesPage } from "@/pages/Sources"
import { ContactDetailPage, ContactsPage } from "@/pages/projects/ContactPages"
import { JobDetailPage, JobListPage } from "@/pages/projects/JobPages"
import { ProjectDetailPage } from "@/pages/projects/ProjectDetailPage"
import { ProjectForm } from "@/pages/projects/ProjectForm"
import { ProjectsListPage } from "@/pages/projects/ProjectsList"
import { ProjectSettingsPage } from "@/pages/projects/ProjectSettingsPage"
import { SourceDetailPage, SourceFormPage } from "@/pages/projects/SourcePages"
import { TagsPage, ProductsPage } from "@/pages/projects/TagProductPages"

// Route paths deliberately mirror the legacy Django URLs so bookmarks keep working.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "projects", element: <ProjectsListPage /> },
      {
        path: "projects/new",
        element: (
          <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">Create project</h1>
            <ProjectForm />
          </div>
        ),
      },
      { path: "projects/:projectId", element: <ProjectDetailPage /> },
      { path: "projects/:projectId/settings", element: <ProjectSettingsPage /> },
      { path: "projects/:projectId/sources/new", element: <SourceFormPage /> },
      { path: "projects/:projectId/sources/:sourceId", element: <SourceDetailPage /> },
      { path: "projects/:projectId/sources/:sourceId/edit", element: <SourceFormPage edit /> },
      { path: "projects/:projectId/jobs", element: <JobListPage /> },
      { path: "projects/:projectId/jobs/:jobId", element: <JobDetailPage /> },
      { path: "projects/:projectId/contacts", element: <ContactsPage /> },
      { path: "projects/:projectId/contacts/:contactId", element: <ContactDetailPage /> },
      { path: "projects/:projectId/tags", element: <TagsPage /> },
      { path: "projects/:projectId/products", element: <ProductsPage /> },
      { path: "opportunities", element: <OpportunitiesPage /> },
      { path: "opportunities/:candidateId", element: <OpportunityDetailPage /> },
      { path: "conversations", element: <ConversationsPage /> },
      { path: "knowledge", element: <KnowledgePage /> },
      { path: "data-quality", element: <DataQualityPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "*", element: <Placeholder title="Not found" /> },
    ],
  },
])
