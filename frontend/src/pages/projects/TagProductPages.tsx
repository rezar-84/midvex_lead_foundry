import { useState } from "react"
import { useParams, useSearchParams } from "react-router"

import {
  useCreateProduct,
  useCreateTag,
  useProducts,
  useTags,
} from "@/api/queries"
import { RequestError } from "@/api/client"
import { CapabilityGate } from "@/components/CapabilityGate"
import { EmptyState, Pagination } from "@/components/shared"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { ProjectNav } from "./ProjectDetailPage"

export function TagsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const { data: tags, isPending } = useTags(projectId ?? "")
  const create = useCreateTag(projectId ?? "")
  const [form, setForm] = useState({ name: "", category: "", color: "#466653" })

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Tags</h1>
      <ProjectNav projectId={projectId ?? ""} active="tags" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          {isPending ? (
            <Skeleton className="h-40 w-full" />
          ) : tags && tags.length > 0 ? (
            <ul className="space-y-2">
              {tags.map((tag) => (
                <li key={tag.id} className="neu-flat flex items-center gap-3 p-3">
                  <span
                    className="size-4 rounded-full"
                    style={{ backgroundColor: tag.color }}
                    aria-hidden
                  />
                  <span className="font-medium">{tag.name}</span>
                  <Badge variant="secondary">{tag.category}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No tags yet">
              Create tags to categorise contacts across this project.
            </EmptyState>
          )}
        </div>
        <CapabilityGate capability="run_batches">
          <div className="neu-raised space-y-4 p-5">
            <h2 className="font-semibold">Create tag</h2>
            <div className="space-y-2">
              <Label htmlFor="tag-name">Name</Label>
              <Input
                id="tag-name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tag-category">Category</Label>
              <Input
                id="tag-category"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tag-color">Color</Label>
              <Input
                id="tag-color"
                type="color"
                className="h-9 w-20 p-1"
                value={form.color}
                onChange={(e) => setForm({ ...form, color: e.target.value })}
              />
            </div>
            <Button
              size="sm"
              disabled={!form.name || !form.category || create.isPending}
              onClick={() =>
                create.mutate(form, {
                  onSuccess: () => setForm({ name: "", category: "", color: "#466653" }),
                })
              }
            >
              Create tag
            </Button>
            {create.isError ? (
              <p className="text-sm text-destructive">{create.error.message}</p>
            ) : null}
          </div>
        </CapabilityGate>
      </div>
    </div>
  )
}

export function ProductsPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [params, setParams] = useSearchParams()
  const page = Number(params.get("page") ?? "1")
  const { data, isPending } = useProducts(projectId ?? "", page)
  const create = useCreateProduct(projectId ?? "")
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    canonical_name: "",
    aliases_text: "",
    product_group: "",
    description: "",
    status: "candidate",
  })
  const errors = create.error instanceof RequestError ? create.error.error.fields : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Products</h1>
        <CapabilityGate capability="run_batches">
          <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Close" : "Add product"}
          </Button>
        </CapabilityGate>
      </div>
      <ProjectNav projectId={projectId ?? ""} active="products" />
      {showForm ? (
        <div className="neu-raised max-w-xl space-y-4 p-5">
          <div className="space-y-2">
            <Label htmlFor="product-name">Canonical name</Label>
            <Input
              id="product-name"
              value={form.canonical_name}
              onChange={(e) => setForm({ ...form, canonical_name: e.target.value })}
            />
            {errors?.canonical_name ? (
              <p className="text-sm text-destructive">{String(errors.canonical_name)}</p>
            ) : null}
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-aliases">Aliases (one per line)</Label>
            <Textarea
              id="product-aliases"
              rows={3}
              value={form.aliases_text}
              onChange={(e) => setForm({ ...form, aliases_text: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-group">Product group</Label>
            <Input
              id="product-group"
              value={form.product_group}
              onChange={(e) => setForm({ ...form, product_group: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="product-description">Description</Label>
            <Textarea
              id="product-description"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <Button
            size="sm"
            disabled={!form.canonical_name || create.isPending}
            onClick={() =>
              create.mutate(form, {
                onSuccess: () => {
                  setShowForm(false)
                  setForm({
                    canonical_name: "",
                    aliases_text: "",
                    product_group: "",
                    description: "",
                    status: "candidate",
                  })
                },
              })
            }
          >
            Create product
          </Button>
        </div>
      ) : null}
      {isPending || !data ? (
        <Skeleton className="h-48 w-full" />
      ) : data.items.length > 0 ? (
        <>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {data.items.map((product) => (
              <div key={product.id} className="neu-flat space-y-2 p-5">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="font-semibold">{product.canonical_name}</h2>
                  <Badge variant="secondary" className="capitalize">
                    {product.status}
                  </Badge>
                </div>
                {product.product_group ? (
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    {product.product_group}
                  </p>
                ) : null}
                {product.description ? (
                  <p className="line-clamp-3 text-sm text-muted-foreground">
                    {product.description}
                  </p>
                ) : null}
                {product.aliases.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Also known as: {product.aliases.join(", ")}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
          <Pagination
            page={page}
            data={data}
            onPageChange={(next) => setParams({ page: String(next) })}
          />
        </>
      ) : (
        <EmptyState title="No products yet">
          Products appear here as analysis extracts them, or add one manually.
        </EmptyState>
      )}
    </div>
  )
}
