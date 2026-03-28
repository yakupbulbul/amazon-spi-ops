import {
  AlertTriangle,
  CheckCheck,
  FileJson2,
  FilePenLine,
  Lightbulb,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import { startTransition, useEffect, useEffectEvent, useState } from "react";

import { useAuth } from "../hooks/useAuth";
import {
  generateAplusDraft,
  getAplusDrafts,
  getProducts,
  publishAplusDraft,
  type AplusDraftPayload,
  type AplusDraftResponse,
  type AplusModulePayload,
  type AplusPublishResponse,
  type ProductListItem,
  validateAplusDraft,
} from "../lib/api";

const moduleLabels: Record<AplusModulePayload["module_type"], string> = {
  hero: "Hero",
  feature: "Feature",
  comparison: "Comparison",
  faq: "FAQ",
};

const defaultModuleOrder: AplusModulePayload["module_type"][] = [
  "hero",
  "feature",
  "comparison",
];

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function buildEmptyDraft(product?: ProductListItem | null): AplusDraftPayload {
  const brandLabel = product?.brand ?? "Brand";
  const titleLabel = product?.title ?? "Product";

  return {
    headline: `${brandLabel} for ${titleLabel}`,
    subheadline: "Structured A+ story prepared for marketplace review.",
    brand_story:
      "Summarize the brand angle, core product context, and any grounded differentiators you want the editorial review to protect.",
    key_features: [
      "State the most important product feature",
      "Call out the strongest practical benefit",
      "Add one marketplace-safe proof point",
    ],
    modules: defaultModuleOrder.map((moduleType, index) => ({
      module_type: moduleType,
      headline: `${moduleLabels[moduleType]} module ${index + 1}`,
      body: "Write concise, factual module copy that stays aligned with the live listing details.",
      bullets: [
        "Keep claims specific and verifiable",
        "Prioritize shopper clarity over hype",
      ],
      image_brief: "Describe the supporting image direction for the creative team.",
    })),
    compliance_notes: [
      "Verify every claim against approved listing attributes before publishing.",
      "Replace image briefs with approved creative references during final review.",
    ],
  };
}

function joinLines(items: string[]): string {
  return items.join("\n");
}

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function getEditablePayload(draft: AplusDraftResponse | null): AplusDraftPayload | null {
  if (!draft) {
    return null;
  }

  return structuredClone(draft.validated_payload ?? draft.draft_payload);
}

export function AplusStudioPage() {
  const { token } = useAuth();
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [drafts, setDrafts] = useState<AplusDraftResponse[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const [brandTone, setBrandTone] = useState("");
  const [positioning, setPositioning] = useState("");
  const [editorDraft, setEditorDraft] = useState<AplusDraftPayload | null>(null);
  const [publishResult, setPublishResult] = useState<AplusPublishResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const selectedDraft = drafts.find((draft) => draft.id === selectedDraftId) ?? null;
  const selectedProduct =
    products.find((product) => product.id === selectedProductId) ??
    products.find((product) => product.id === selectedDraft?.product_id) ??
    null;

  const loadStudioData = useEffectEvent(async ({ cancelled = false }: { cancelled?: boolean } = {}) => {
    if (!token) {
      return;
    }

    try {
      const [productsResponse, draftsResponse] = await Promise.all([
        getProducts(token),
        getAplusDrafts(token),
      ]);

      if (cancelled) {
        return;
      }

      startTransition(() => {
        setProducts(productsResponse.items);
        setDrafts(draftsResponse.items);
        setError(null);
      });

      if (!selectedProductId && productsResponse.items[0]) {
        setSelectedProductId(productsResponse.items[0].id);
      }

      if (!selectedDraftId && draftsResponse.items[0]) {
        const newestDraft = draftsResponse.items[0];
        setSelectedDraftId(newestDraft.id);
        setSelectedProductId(newestDraft.product_id);
        setBrandTone(newestDraft.brand_tone ?? "");
        setPositioning(newestDraft.positioning ?? "");
        setEditorDraft(getEditablePayload(newestDraft));
      } else if (!draftsResponse.items.length && !editorDraft) {
        setEditorDraft(buildEmptyDraft(productsResponse.items[0] ?? null));
      }
    } catch (loadError) {
      if (!cancelled) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load A+ Studio.");
      }
    } finally {
      if (!cancelled) {
        setIsLoading(false);
      }
    }
  });

  useEffect(() => {
    let cancelled = false;
    void loadStudioData({ cancelled });
    return () => {
      cancelled = true;
    };
  }, [loadStudioData, token]);

  useEffect(() => {
    if (!selectedProductId || selectedDraftId) {
      return;
    }

    const activeProduct = products.find((product) => product.id === selectedProductId) ?? null;
    setEditorDraft(buildEmptyDraft(activeProduct));
  }, [products, selectedDraftId, selectedProductId]);

  function upsertDraft(nextDraft: AplusDraftResponse) {
    setDrafts((currentDrafts) => [
      nextDraft,
      ...currentDrafts.filter((draft) => draft.id !== nextDraft.id),
    ]);
  }

  function selectDraft(draft: AplusDraftResponse) {
    setSelectedDraftId(draft.id);
    setSelectedProductId(draft.product_id);
    setBrandTone(draft.brand_tone ?? "");
    setPositioning(draft.positioning ?? "");
    setEditorDraft(getEditablePayload(draft));
    setPublishResult(null);
    setError(null);
  }

  async function handleGenerate() {
    if (!token || !selectedProductId) {
      setError("Select a product before generating an A+ draft.");
      return;
    }

    setIsGenerating(true);
    setError(null);
    setStatusMessage(null);
    setPublishResult(null);

    try {
      const draft = await generateAplusDraft(token, {
        product_id: selectedProductId,
        brand_tone: brandTone || undefined,
        positioning: positioning || undefined,
      });

      upsertDraft(draft);
      selectDraft(draft);
      setStatusMessage("Draft generated. Review and refine the copy before validation.");
    } catch (generateError) {
      setError(
        generateError instanceof Error ? generateError.message : "Unable to generate A+ draft.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleValidate() {
    if (!token || !selectedDraftId || !editorDraft) {
      setError("Generate or select a draft before validating it.");
      return;
    }

    setIsValidating(true);
    setError(null);
    setStatusMessage(null);

    try {
      const draft = await validateAplusDraft(token, {
        draft_id: selectedDraftId,
        draft_payload: editorDraft,
      });

      upsertDraft(draft);
      selectDraft(draft);
      setStatusMessage("Draft validated and saved. The validated payload is ready for publish preview.");
    } catch (validateError) {
      setError(
        validateError instanceof Error ? validateError.message : "Unable to validate A+ draft.",
      );
    } finally {
      setIsValidating(false);
    }
  }

  async function handlePublish() {
    if (!token || !selectedDraftId) {
      setError("Select a draft before preparing the publish payload.");
      return;
    }

    setIsPublishing(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await publishAplusDraft(token, selectedDraftId);
      upsertDraft(response.draft);
      selectDraft(response.draft);
      setPublishResult(response);
      setStatusMessage(response.message);
    } catch (publishError) {
      setError(
        publishError instanceof Error ? publishError.message : "Unable to publish A+ draft.",
      );
    } finally {
      setIsPublishing(false);
    }
  }

  function handleProductChange(productId: string) {
    setSelectedProductId(productId);
    setSelectedDraftId(null);
    setPublishResult(null);
    const nextProduct = products.find((product) => product.id === productId) ?? null;
    setEditorDraft(buildEmptyDraft(nextProduct));
  }

  function updateModule(
    index: number,
    patch: Partial<AplusModulePayload>,
  ) {
    setEditorDraft((currentDraft) => {
      if (!currentDraft) {
        return currentDraft;
      }

      const nextModules = currentDraft.modules.map((module, moduleIndex) =>
        moduleIndex === index ? { ...module, ...patch } : module,
      );

      return {
        ...currentDraft,
        modules: nextModules,
      };
    });
  }

  function addModule() {
    setEditorDraft((currentDraft) => {
      if (!currentDraft || currentDraft.modules.length >= 5) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        modules: [
          ...currentDraft.modules,
          {
            module_type: "feature",
            headline: "New feature module",
            body: "Add factual supporting copy for this additional content block.",
            bullets: ["State the core supporting point", "Keep the language marketplace safe"],
            image_brief: "Describe the image angle for this module.",
          },
        ],
      };
    });
  }

  function removeModule(index: number) {
    setEditorDraft((currentDraft) => {
      if (!currentDraft || currentDraft.modules.length <= 3) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        modules: currentDraft.modules.filter((_, moduleIndex) => moduleIndex !== index),
      };
    });
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
        <div className="rounded-[2rem] border border-white/10 bg-[linear-gradient(135deg,_rgba(14,165,233,0.18),_rgba(15,23,42,0.94)_38%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-sky-100/70">A+ Content Studio</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Generate structured A+ drafts, refine them in place, and preview the Amazon-ready payload.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            This workflow pulls live catalog products, sends a structured prompt to OpenAI, validates
            the resulting JSON, and prepares a publish payload without exposing secrets to the client.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Drafts</p>
            <p className="mt-4 text-4xl font-semibold text-white">{drafts.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Stored A+ concepts ready for editorial review.</p>
          </article>
          <article className="rounded-[1.75rem] border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Selected product</p>
            <p className="mt-4 text-2xl font-semibold text-white">
              {selectedProduct?.sku ?? "Choose a product"}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {selectedProduct ? selectedProduct.title : "Start by choosing a live Amazon listing."}
            </p>
          </article>
        </div>
      </section>

      {error ? (
        <section className="flex items-start gap-3 rounded-[1.5rem] border border-rose-400/20 bg-rose-500/10 px-5 py-4 text-sm text-rose-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </section>
      ) : null}

      {statusMessage ? (
        <section className="flex items-start gap-3 rounded-[1.5rem] border border-emerald-400/20 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-100">
          <CheckCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{statusMessage}</span>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[380px_minmax(0,1fr)]">
        <div className="space-y-6">
          <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <Sparkles className="h-5 w-5 text-sky-200" />
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Prompt controls</p>
                <h3 className="mt-1 text-xl font-semibold text-white">Generate draft</h3>
              </div>
            </div>

            <div className="mt-6 space-y-4">
              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Product</span>
                <select
                  value={selectedProductId}
                  onChange={(event) => handleProductChange(event.target.value)}
                  className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                >
                  {products.length ? null : <option value="">No products available</option>}
                  {products.map((product) => (
                    <option key={product.id} value={product.id} className="bg-slate-950">
                      {product.sku} · {product.title}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Brand tone</span>
                <input
                  type="text"
                  value={brandTone}
                  onChange={(event) => setBrandTone(event.target.value)}
                  placeholder="Measured, premium, performance-led"
                  className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm text-slate-300">Positioning</span>
                <textarea
                  value={positioning}
                  onChange={(event) => setPositioning(event.target.value)}
                  rows={4}
                  placeholder="Explain the usage context, customer segment, and any grounded purchase angle."
                  className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500"
                />
              </label>
            </div>

            <button
              type="button"
              onClick={() => void handleGenerate()}
              disabled={isLoading || isGenerating || !selectedProductId}
              className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-[1.25rem] bg-amber-300 px-5 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
            >
              <Sparkles className="h-4 w-4" />
              <span>{isGenerating ? "Generating draft..." : "Generate A+ draft"}</span>
            </button>
          </article>

          <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
            <div className="flex items-center gap-3">
              <FilePenLine className="h-5 w-5 text-amber-200" />
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Draft history</p>
                <h3 className="mt-1 text-xl font-semibold text-white">Recent drafts</h3>
              </div>
            </div>

            {isLoading ? (
              <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
                Loading A+ Studio data...
              </div>
            ) : drafts.length === 0 ? (
              <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-4 text-sm leading-6 text-slate-400">
                No A+ drafts yet. Generate the first draft from a live catalog product.
              </div>
            ) : (
              <div className="mt-6 space-y-3">
                {drafts.slice(0, 8).map((draft) => (
                  <button
                    key={draft.id}
                    type="button"
                    onClick={() => selectDraft(draft)}
                    className={[
                      "w-full rounded-[1.5rem] border px-4 py-4 text-left transition",
                      draft.id === selectedDraftId
                        ? "border-sky-300/30 bg-sky-500/10"
                        : "border-white/10 bg-white/[0.03] hover:bg-white/[0.06]",
                    ].join(" ")}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-white">{draft.product_title}</p>
                        <p className="mt-1 text-xs uppercase tracking-[0.24em] text-slate-500">
                          {draft.product_sku} · {draft.status.replaceAll("_", " ")}
                        </p>
                      </div>
                      <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
                        {draft.marketplace_id}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-400">
                      Updated {formatTimestamp(draft.updated_at)}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </article>
        </div>

        <div className="space-y-6">
          <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Editor</p>
                <h3 className="mt-2 text-2xl font-semibold text-white">
                  {selectedDraft ? selectedDraft.product_title : "Draft editor"}
                </h3>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
                  Edit the structured JSON fields directly. Validation persists the edited payload,
                  and publish prepares the Amazon-compatible document preview.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => void handleValidate()}
                  disabled={!selectedDraftId || !editorDraft || isValidating}
                  className="rounded-[1.25rem] border border-sky-300/20 bg-sky-500/10 px-4 py-3 text-sm font-medium text-sky-100 transition hover:bg-sky-500/20 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isValidating ? "Validating..." : "Validate draft"}
                </button>
                <button
                  type="button"
                  onClick={() => void handlePublish()}
                  disabled={!selectedDraftId || isPublishing}
                  className="rounded-[1.25rem] bg-amber-300 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isPublishing ? "Preparing..." : "Prepare publish payload"}
                </button>
              </div>
            </div>

            {!editorDraft ? (
              <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
                Generate a draft or select an existing draft to start editing the A+ payload.
              </div>
            ) : (
              <div className="mt-6 space-y-6">
                <div className="grid gap-4 lg:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Headline</span>
                    <input
                      type="text"
                      value={editorDraft.headline}
                      onChange={(event) =>
                        setEditorDraft((currentDraft) =>
                          currentDraft
                            ? {
                                ...currentDraft,
                                headline: event.target.value,
                              }
                            : currentDraft,
                        )
                      }
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                    />
                  </label>

                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Subheadline</span>
                    <input
                      type="text"
                      value={editorDraft.subheadline}
                      onChange={(event) =>
                        setEditorDraft((currentDraft) =>
                          currentDraft
                            ? {
                                ...currentDraft,
                                subheadline: event.target.value,
                              }
                            : currentDraft,
                        )
                      }
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                    />
                  </label>
                </div>

                <label className="block space-y-2">
                  <span className="text-sm text-slate-300">Brand story</span>
                  <textarea
                    value={editorDraft.brand_story}
                    onChange={(event) =>
                      setEditorDraft((currentDraft) =>
                        currentDraft
                          ? {
                              ...currentDraft,
                              brand_story: event.target.value,
                            }
                          : currentDraft,
                      )
                    }
                    rows={5}
                    className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-white outline-none"
                  />
                </label>

                <div className="grid gap-4 lg:grid-cols-2">
                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Key features</span>
                    <textarea
                      value={joinLines(editorDraft.key_features)}
                      onChange={(event) =>
                        setEditorDraft((currentDraft) =>
                          currentDraft
                            ? {
                                ...currentDraft,
                                key_features: parseLines(event.target.value),
                              }
                            : currentDraft,
                        )
                      }
                      rows={6}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-sm leading-6 text-white outline-none"
                    />
                  </label>

                  <label className="block space-y-2">
                    <span className="text-sm text-slate-300">Compliance notes</span>
                    <textarea
                      value={joinLines(editorDraft.compliance_notes)}
                      onChange={(event) =>
                        setEditorDraft((currentDraft) =>
                          currentDraft
                            ? {
                                ...currentDraft,
                                compliance_notes: parseLines(event.target.value),
                              }
                            : currentDraft,
                        )
                      }
                      rows={6}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-sm leading-6 text-white outline-none"
                    />
                  </label>
                </div>

                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">Content modules</p>
                      <p className="mt-1 text-sm text-slate-400">
                        Keep between 3 and 5 modules to satisfy the current backend validation rules.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={addModule}
                      disabled={editorDraft.modules.length >= 5}
                      className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <Plus className="h-4 w-4" />
                      Add module
                    </button>
                  </div>

                  <div className="space-y-4">
                    {editorDraft.modules.map((module, index) => (
                      <article
                        key={`${module.module_type}-${index}`}
                        className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-4"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-3">
                          <div className="flex items-center gap-3">
                            <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs uppercase tracking-[0.22em] text-slate-400">
                              Module {index + 1}
                            </span>
                            <select
                              value={module.module_type}
                              onChange={(event) =>
                                updateModule(index, {
                                  module_type: event.target.value as AplusModulePayload["module_type"],
                                })
                              }
                              className="rounded-full border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white outline-none"
                            >
                              {Object.entries(moduleLabels).map(([value, label]) => (
                                <option key={value} value={value} className="bg-slate-950">
                                  {label}
                                </option>
                              ))}
                            </select>
                          </div>

                          <button
                            type="button"
                            onClick={() => removeModule(index)}
                            disabled={editorDraft.modules.length <= 3}
                            className="inline-flex items-center gap-2 rounded-full border border-rose-300/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-100 transition hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <Trash2 className="h-4 w-4" />
                            Remove
                          </button>
                        </div>

                        <div className="mt-4 grid gap-4 lg:grid-cols-2">
                          <label className="block space-y-2 lg:col-span-2">
                            <span className="text-sm text-slate-300">Headline</span>
                            <input
                              type="text"
                              value={module.headline}
                              onChange={(event) => updateModule(index, { headline: event.target.value })}
                              className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-white outline-none"
                            />
                          </label>

                          <label className="block space-y-2 lg:col-span-2">
                            <span className="text-sm text-slate-300">Body</span>
                            <textarea
                              value={module.body}
                              onChange={(event) => updateModule(index, { body: event.target.value })}
                              rows={4}
                              className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-white outline-none"
                            />
                          </label>

                          <label className="block space-y-2">
                            <span className="text-sm text-slate-300">Bullets</span>
                            <textarea
                              value={joinLines(module.bullets)}
                              onChange={(event) =>
                                updateModule(index, { bullets: parseLines(event.target.value) })
                              }
                              rows={4}
                              className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-sm leading-6 text-white outline-none"
                            />
                          </label>

                          <label className="block space-y-2">
                            <span className="text-sm text-slate-300">Image brief</span>
                            <textarea
                              value={module.image_brief}
                              onChange={(event) =>
                                updateModule(index, { image_brief: event.target.value })
                              }
                              rows={4}
                              className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-white outline-none"
                            />
                          </label>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </article>

          <section className="grid gap-6 2xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
              <div className="flex items-center gap-3">
                <Lightbulb className="h-5 w-5 text-amber-200" />
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Preview</p>
                  <h3 className="mt-1 text-xl font-semibold text-white">Editorial view</h3>
                </div>
              </div>

              {!editorDraft ? null : (
                <div className="mt-6 space-y-5">
                  <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Headline</p>
                    <h4 className="mt-3 text-2xl font-semibold text-white">{editorDraft.headline}</h4>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{editorDraft.subheadline}</p>
                  </div>

                  <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Brand story</p>
                    <p className="mt-3 text-sm leading-7 text-slate-300">{editorDraft.brand_story}</p>
                  </div>

                  <div className="rounded-[1.5rem] border border-white/10 bg-white/[0.03] p-5">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Key features</p>
                    <div className="mt-4 space-y-3">
                      {editorDraft.key_features.map((feature) => (
                        <div key={feature} className="rounded-[1.25rem] bg-slate-900/70 px-4 py-3 text-sm text-slate-200">
                          {feature}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </article>

            <article className="rounded-[1.75rem] border border-white/10 bg-slate-950/50 p-5 sm:p-6">
              <div className="flex items-center gap-3">
                <FileJson2 className="h-5 w-5 text-sky-200" />
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Publish payload</p>
                  <h3 className="mt-1 text-xl font-semibold text-white">Amazon-compatible preview</h3>
                </div>
              </div>

              {publishResult ? (
                <div className="mt-6 space-y-4">
                  <div className="rounded-[1.5rem] border border-emerald-400/20 bg-emerald-500/10 p-4 text-sm leading-6 text-emerald-100">
                    Publish job {publishResult.publish_job_id} completed with status {publishResult.status}.
                  </div>
                  <pre className="overflow-x-auto rounded-[1.5rem] border border-white/10 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-200">
                    {JSON.stringify(publishResult.prepared_payload, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
                  Prepare the publish payload to inspect the Amazon-compatible JSON that will be sent
                  by the backend publish workflow.
                </div>
              )}
            </article>
          </section>
        </div>
      </section>
    </div>
  );
}
