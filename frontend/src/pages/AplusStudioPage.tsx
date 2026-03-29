import {
  AlertTriangle,
  CheckCheck,
  FileJson2,
  FilePenLine,
  MonitorSmartphone,
  LoaderCircle,
  Plus,
  Sparkles,
} from "lucide-react";
import { startTransition, useEffect, useEffectEvent, useRef, useState } from "react";

import { AplusModuleEditorCard } from "../components/aplus/AplusModuleEditorCard";
import { AplusOptimizationPanel } from "../components/aplus/AplusOptimizationPanel";
import { AplusPreviewModal } from "../components/aplus/AplusPreviewModal";
import { AplusReadinessPanel } from "../components/aplus/AplusReadinessPanel";
import { AplusScoreBadge } from "../components/aplus/AplusScoreBadge";
import { AplusSectionWarnings } from "../components/aplus/AplusSectionWarnings";
import { DraftMetadataBar } from "../components/aplus/DraftMetadataBar";
import { LanguageSelector } from "../components/aplus/LanguageSelector";
import { ProductCombobox } from "../components/aplus/ProductCombobox";
import { TranslationToggle } from "../components/aplus/TranslationToggle";
import {
  formatLanguageLabel,
  getDefaultTargetLanguage,
} from "../components/aplus/languages";
import { useAuth } from "../hooks/useAuth";
import {
  generateAplusDraft,
  generateAplusModuleImage,
  getAplusAssets,
  getAplusDrafts,
  getProducts,
  publishAplusDraft,
  uploadAplusAsset,
  type AplusAsset,
  type AplusDraftPayload,
  type AplusDraftResponse,
  type AplusLanguage,
  type AplusModulePayload,
  type AplusOptimizationSuggestion,
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

function createModuleId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID().replaceAll("-", "");
  }
  return `${Date.now().toString(16)}${Math.random().toString(16).slice(2, 10)}`;
}

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
      module_id: createModuleId(),
      module_type: moduleType,
      headline: `${moduleLabels[moduleType]} module ${index + 1}`,
      body: "Write concise, factual module copy that stays aligned with the live listing details.",
      bullets: [
        "Keep claims specific and verifiable",
        "Prioritize shopper clarity over hype",
      ],
      image_brief: "Describe the supporting image direction for the creative team.",
      image_mode: "none",
      image_prompt: null,
      generated_image_url: null,
      uploaded_image_url: null,
      selected_asset_id: null,
      reference_asset_ids: [],
      overlay_text: null,
      image_status: "idle",
      image_error_message: null,
      image_request_fingerprint: null,
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

function getOptimizationSuggestions(
  draft: AplusDraftResponse | null,
  sections: string[],
): AplusOptimizationSuggestion[] {
  if (!draft) {
    return [];
  }

  const matches = [...draft.optimization_report.critical_issues, ...draft.optimization_report.warnings];
  return matches.filter((item) =>
    sections.some((section) => item.section.toLowerCase().includes(section.toLowerCase())),
  );
}

export function AplusStudioPage() {
  const { token } = useAuth();
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [drafts, setDrafts] = useState<AplusDraftResponse[]>([]);
  const [selectedProductId, setSelectedProductId] = useState("");
  const [selectedDraftId, setSelectedDraftId] = useState<string | null>(null);
  const [brandTone, setBrandTone] = useState("");
  const [positioning, setPositioning] = useState("");
  const [sourceLanguage, setSourceLanguage] = useState<AplusLanguage>("de-DE");
  const [targetLanguage, setTargetLanguage] = useState<AplusLanguage>("de-DE");
  const [autoTranslate, setAutoTranslate] = useState(false);
  const [editorDraft, setEditorDraft] = useState<AplusDraftPayload | null>(null);
  const [assets, setAssets] = useState<AplusAsset[]>([]);
  const [publishResult, setPublishResult] = useState<AplusPublishResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [expandedModules, setExpandedModules] = useState<number[]>([0]);
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);
  const [assetLibraryError, setAssetLibraryError] = useState<string | null>(null);
  const [imageUploadState, setImageUploadState] = useState<
    Record<number, { pending: boolean; error: string | null }>
  >({});
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const previewTriggerRef = useRef<HTMLButtonElement | null>(null);

  const selectedDraft = drafts.find((draft) => draft.id === selectedDraftId) ?? null;
  const selectedProduct =
    products.find((product) => product.id === selectedProductId) ??
    products.find((product) => product.id === selectedDraft?.product_id) ??
    null;

  const generationSourceLanguage = selectedDraft?.source_language ?? sourceLanguage;
  const generationTargetLanguage = selectedDraft?.target_language ?? targetLanguage;
  const generationAutoTranslate = selectedDraft?.auto_translate ?? autoTranslate;
  const selectedDraftPayload = getEditablePayload(selectedDraft);
  const hasUnsavedChanges =
    selectedDraft !== null &&
    editorDraft !== null &&
    JSON.stringify(editorDraft) !== JSON.stringify(selectedDraftPayload);
  const publishReady = selectedDraft?.readiness_report.is_publish_ready ?? false;
  const optimizationScore = selectedDraft?.optimization_report.overall_score ?? null;
  const coreMessageSuggestions = getOptimizationSuggestions(selectedDraft, [
    "hero",
    "headline",
    "benefit",
  ]);
  const brandStorySuggestions = getOptimizationSuggestions(selectedDraft, [
    "brand story",
    "differentiation",
  ]);
  const featureSuggestions = getOptimizationSuggestions(selectedDraft, [
    "feature",
    "technical detail",
    "customer education",
    "usage scenario",
  ]);
  const moduleSuggestions = getOptimizationSuggestions(selectedDraft, [
    "module",
    "comparison",
    "image",
    "cross-section",
  ]);
  const hasPendingImageGeneration =
    selectedDraft?.draft_payload.modules.some(
      (module) => module.image_status === "queued" || module.image_status === "generating",
    ) ?? false;

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
        setSourceLanguage(newestDraft.source_language);
        setTargetLanguage(newestDraft.target_language);
        setAutoTranslate(newestDraft.auto_translate);
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

  useEffect(() => {
    if (!token || !selectedProductId) {
      setAssets([]);
      setAssetLibraryError(null);
      return;
    }

    let cancelled = false;
    setIsLoadingAssets(true);
    void getAplusAssets(token, selectedProductId)
      .then((response) => {
        if (!cancelled) {
          setAssets(response.items);
          setAssetLibraryError(null);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setAssetLibraryError(
            loadError instanceof Error ? loadError.message : "Unable to load reusable assets.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingAssets(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedProductId, token]);

  useEffect(() => {
    if (!token || !selectedDraftId || !hasPendingImageGeneration) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void getAplusDrafts(token)
        .then((response) => {
          const nextDraft = response.items.find((item) => item.id === selectedDraftId);
          if (!nextDraft) {
            return;
          }

          upsertDraft(nextDraft);
          if (!hasUnsavedChanges) {
            selectDraft(nextDraft);
          }
        })
        .catch(() => {
          // Keep polling passive. Existing error banners already cover explicit user actions.
        });
    }, 3000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [hasPendingImageGeneration, hasUnsavedChanges, selectedDraftId, token]);

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
    setSourceLanguage(draft.source_language);
    setTargetLanguage(draft.target_language);
    setAutoTranslate(draft.auto_translate);
    setEditorDraft(getEditablePayload(draft));
    setExpandedModules([0]);
    setPublishResult(null);
    setError(null);
  }

  async function handleGenerate() {
    if (!token || !selectedProductId) {
      setError("Select a product before generating an A+ draft.");
      return;
    }

    const effectiveTargetLanguage = autoTranslate ? targetLanguage : sourceLanguage;
    if (autoTranslate && sourceLanguage === effectiveTargetLanguage) {
      setError("Choose a different target language when auto-translate is enabled.");
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
        source_language: sourceLanguage,
        target_language: effectiveTargetLanguage,
        auto_translate: autoTranslate,
      });

      upsertDraft(draft);
      selectDraft(draft);
      setStatusMessage(
        autoTranslate
          ? `Draft generated in ${formatLanguageLabel(sourceLanguage)} and translated into ${formatLanguageLabel(effectiveTargetLanguage)}.`
          : `Draft generated in ${formatLanguageLabel(sourceLanguage)}. Review and refine it before validation.`,
      );
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
      if (draft.readiness_report.is_publish_ready) {
        setStatusMessage(
          "Draft validated and marked publish-ready. The current payload can now be prepared for publish.",
        );
      } else {
        setStatusMessage(
          `Draft validated with ${draft.readiness_report.blocking_errors.length} blocking issue(s) and ${draft.readiness_report.warnings.length} warning(s). Review the publish readiness panel before continuing.`,
        );
      }
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
    setExpandedModules([0]);
  }

  function handleSourceLanguageChange(nextLanguage: AplusLanguage) {
    setSourceLanguage(nextLanguage);
    if (!autoTranslate) {
      setTargetLanguage(nextLanguage);
      return;
    }

    if (targetLanguage === nextLanguage) {
      setTargetLanguage(getDefaultTargetLanguage(nextLanguage));
    }
  }

  function handleAutoTranslateChange(nextValue: boolean) {
    setAutoTranslate(nextValue);
    if (!nextValue) {
      setTargetLanguage(sourceLanguage);
      return;
    }

    if (targetLanguage === sourceLanguage) {
      setTargetLanguage(getDefaultTargetLanguage(sourceLanguage));
    }
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

  async function handleModuleImageUpload(index: number, file: File) {
    if (!token || !selectedProductId || !editorDraft) {
      setError("Select a product before uploading module images.");
      return;
    }

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setImageUploadState((current) => ({
        ...current,
        [index]: { pending: false, error: "Only JPG, PNG, and WEBP files are supported." },
      }));
      return;
    }

    if (file.size > 8 * 1024 * 1024) {
      setImageUploadState((current) => ({
        ...current,
        [index]: { pending: false, error: "Images must be 8 MB or smaller." },
      }));
      return;
    }

    setImageUploadState((current) => ({
      ...current,
      [index]: { pending: true, error: null },
    }));

    try {
      const asset = await uploadAplusAsset(token, {
        file,
        asset_scope: selectedProduct?.brand ? "product" : "brand",
        product_id: selectedProductId,
        label: `${selectedProduct?.sku ?? "Asset"} · ${editorDraft.modules[index]?.headline ?? "Module image"}`,
      });

      setAssets((currentAssets) => [asset, ...currentAssets.filter((item) => item.id !== asset.id)]);
      updateModule(index, {
        image_mode: "uploaded",
        uploaded_image_url: asset.public_url,
        selected_asset_id: asset.id,
        generated_image_url: null,
        image_status: "completed",
        image_error_message: null,
        image_request_fingerprint: null,
      });
      setImageUploadState((current) => ({
        ...current,
        [index]: { pending: false, error: null },
      }));
    } catch (uploadError) {
      setImageUploadState((current) => ({
        ...current,
        [index]: {
          pending: false,
          error: uploadError instanceof Error ? uploadError.message : "Unable to upload image.",
        },
      }));
    }
  }

  function attachExistingAsset(index: number, asset: AplusAsset) {
    updateModule(index, {
      image_mode: "existing_asset",
      selected_asset_id: asset.id,
      uploaded_image_url: null,
      generated_image_url: null,
      image_status: "completed",
      image_error_message: null,
      image_request_fingerprint: null,
    });
  }

  function clearModuleImage(index: number) {
    updateModule(index, {
      image_mode: "none",
      uploaded_image_url: null,
      generated_image_url: null,
      selected_asset_id: null,
      image_status: "idle",
      image_error_message: null,
      image_request_fingerprint: null,
    });
  }

  async function handleGenerateModuleImage(index: number) {
    if (!token || !selectedDraftId || !editorDraft) {
      setError("Generate a draft before creating AI images.");
      return;
    }

    if (hasUnsavedChanges) {
      setError("Validate or save the current draft before running background image generation.");
      return;
    }

    const module = editorDraft.modules[index];
    try {
      const draft = await generateAplusModuleImage(token, {
        draft_id: selectedDraftId,
        module_id: module.module_id,
        image_prompt: module.image_prompt,
        overlay_text: module.overlay_text,
        reference_asset_ids: module.reference_asset_ids,
      });
      upsertDraft(draft);
      selectDraft(draft);
      setStatusMessage(`Image generation queued for module ${index + 1}.`);
      setError(null);
    } catch (generationError) {
      setError(
        generationError instanceof Error
          ? generationError.message
          : "Unable to queue module image generation.",
      );
    }
  }

  function addModule() {
    const nextModuleIndex = editorDraft?.modules.length ?? 0;
    setEditorDraft((currentDraft) => {
      if (!currentDraft || currentDraft.modules.length >= 5) {
        return currentDraft;
      }

      return {
        ...currentDraft,
        modules: [
          ...currentDraft.modules,
          {
            module_id: createModuleId(),
            module_type: "feature",
            headline: "New feature module",
            body: "Add factual supporting copy for this additional content block.",
            bullets: ["State the core supporting point", "Keep the language marketplace safe"],
            image_brief: "Describe the image angle for this module.",
            image_mode: "none",
            image_prompt: null,
            generated_image_url: null,
            uploaded_image_url: null,
            selected_asset_id: null,
            reference_asset_ids: [],
            overlay_text: null,
            image_status: "idle",
            image_error_message: null,
            image_request_fingerprint: null,
          },
        ],
      };
    });
    setExpandedModules((current) => [...new Set([...current, nextModuleIndex])]);
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
    setExpandedModules((current) =>
      current
        .filter((moduleIndex) => moduleIndex !== index)
        .map((moduleIndex) => (moduleIndex > index ? moduleIndex - 1 : moduleIndex)),
    );
  }

  function toggleModule(index: number) {
    setExpandedModules((current) =>
      current.includes(index) ? current.filter((item) => item !== index) : [...current, index],
    );
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_320px]">
        <div className="rounded-[2rem] bg-[linear-gradient(135deg,_rgba(14,165,233,0.18),_rgba(15,23,42,0.94)_38%,_rgba(2,6,23,1)_100%)] p-6 shadow-2xl shadow-black/30 sm:p-8">
          <p className="text-xs uppercase tracking-[0.32em] text-sky-100/70">A+ Content Studio</p>
          <h2 className="mt-4 max-w-3xl text-3xl font-semibold leading-tight text-white sm:text-4xl">
            Generate multilingual A+ drafts with faster product discovery and clearer language control.
          </h2>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-300 sm:text-base">
            Search the product catalog instantly, choose the output language, optionally translate
            the structured draft into another locale, and keep the editor and publish preview aligned.
          </p>
          <div className="mt-6 flex flex-wrap gap-2">
            <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
              Searchable product discovery
            </span>
            <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-200">
              Multilingual generation
            </span>
            <span className="rounded-full border border-sky-300/20 bg-sky-500/10 px-3 py-1.5 text-xs text-sky-100">
              Structured translation safe
            </span>
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
          <article className="rounded-[1.75rem] bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Drafts</p>
            <p className="mt-4 text-4xl font-semibold text-white">{drafts.length}</p>
            <p className="mt-3 text-sm leading-6 text-slate-500">Stored A+ concepts ready for editorial review.</p>
          </article>
          <article className="rounded-[1.75rem] bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Current output language</p>
            <p className="mt-4 text-2xl font-semibold text-white">
              {formatLanguageLabel(generationTargetLanguage)}
            </p>
            <p className="mt-3 text-sm leading-6 text-slate-500">
              {generationAutoTranslate
                ? `Generated in ${formatLanguageLabel(generationSourceLanguage)} and translated automatically.`
                : "Generated directly in the selected language."}
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

      <section className="grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)] xl:items-start">
        <div className="space-y-6">
          <article className="rounded-[1.75rem] bg-slate-950/50 p-5 shadow-lg shadow-black/10 sm:p-6">
            <div className="flex items-center gap-3">
              <Sparkles className="h-5 w-5 text-sky-200" />
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Prompt controls</p>
                <h3 className="mt-1 text-xl font-semibold text-white">Generate draft</h3>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Pick the product, choose the language flow, and generate a structured draft.
                </p>
              </div>
            </div>

            <div className="mt-6 space-y-6">
              <section className="space-y-4">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Product</p>
                  <p className="text-sm text-slate-400">Choose the listing that will anchor the A+ story.</p>
                </div>
              <ProductCombobox
                products={products}
                selectedProduct={selectedProduct}
                onSelect={(product) => handleProductChange(product.id)}
                disabled={isLoading || isGenerating}
              />
              </section>

              <div className="h-px bg-white/10" />

              <section className="space-y-4">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Language</p>
                  <p className="text-sm text-slate-400">Define the language used for base generation.</p>
                </div>
              <LanguageSelector
                label="Source language"
                value={sourceLanguage}
                onChange={handleSourceLanguageChange}
                helperText="This is the language used for the original structured generation prompt."
                disabled={isGenerating}
              />
              </section>

              <div className="h-px bg-white/10" />

              <section className="space-y-4">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Translation</p>
                  <p className="text-sm text-slate-400">Translate shopper-facing copy without changing the schema.</p>
                </div>
              <TranslationToggle
                autoTranslate={autoTranslate}
                sourceLanguage={sourceLanguage}
                targetLanguage={targetLanguage}
                onToggle={handleAutoTranslateChange}
                onTargetLanguageChange={setTargetLanguage}
                disabled={isGenerating}
              />
              </section>

              <div className="rounded-[1.25rem] bg-white/[0.03] px-4 py-3 text-sm leading-6 text-slate-300">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Generation flow</p>
                <p className="mt-2">
                  {autoTranslate
                    ? `The base A+ draft will be generated in ${formatLanguageLabel(sourceLanguage)} and then translated into ${formatLanguageLabel(targetLanguage)} while preserving the JSON structure.`
                    : `The A+ draft will be generated directly in ${formatLanguageLabel(sourceLanguage)}.`}
                </p>
              </div>

              <div className="h-px bg-white/10" />

              <section className="space-y-4">
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Brand tone</p>
                  <p className="text-sm text-slate-400">Guide the voice, audience, and positioning.</p>
                </div>
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
                <span className="text-sm text-slate-300">Positioning and customer context</span>
                <textarea
                  value={positioning}
                  onChange={(event) => setPositioning(event.target.value)}
                  rows={4}
                  placeholder="Explain the usage context, customer segment, and any grounded purchase angle."
                  className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-white outline-none placeholder:text-slate-500"
                />
              </label>
              </section>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => void handleGenerate()}
                  disabled={isLoading || isGenerating || !selectedProductId}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-[1.25rem] bg-amber-300 px-5 py-3.5 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Sparkles className="h-4 w-4" />
                  <span>
                    {isGenerating
                      ? autoTranslate
                        ? "Generating and translating draft..."
                        : "Generating draft..."
                      : autoTranslate
                        ? "Generate and translate A+ draft"
                        : "Generate A+ draft"}
                  </span>
                </button>
                <p className="mt-2 text-center text-xs text-slate-500">
                  The generated draft keeps the current JSON contract used by validation and publish.
                </p>
              </div>
            </div>
          </article>

          <article className="rounded-[1.75rem] bg-slate-950/50 p-5 shadow-lg shadow-black/10 sm:p-6">
            <div className="flex items-center gap-3">
              <FilePenLine className="h-5 w-5 text-amber-200" />
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Draft history</p>
                <h3 className="mt-1 text-xl font-semibold text-white">Recent drafts</h3>
                <p className="mt-1 text-xs leading-5 text-slate-500">
                  Jump between recent originals and translated variations.
                </p>
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
                      <div className="flex flex-wrap justify-end gap-2">
                        <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
                          {draft.marketplace_id}
                        </span>
                        <span className="rounded-full border border-sky-300/20 bg-sky-500/10 px-2.5 py-1 text-xs text-sky-100">
                          {draft.auto_translate ? "Translated" : "Original"}
                        </span>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
                        {formatLanguageLabel(draft.source_language)}
                      </span>
                      {draft.auto_translate ? (
                        <span className="rounded-full border border-white/10 px-2.5 py-1 text-xs text-slate-300">
                          {formatLanguageLabel(draft.target_language)}
                        </span>
                      ) : null}
                      <AplusScoreBadge score={draft.optimization_report.overall_score} />
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
          <article className="rounded-[1.75rem] bg-slate-950/50 p-5 shadow-lg shadow-black/10 sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Editor</p>
                <h3 className="mt-2 text-[1.8rem] font-semibold leading-tight text-white">
                  {selectedDraft ? selectedDraft.product_title : "Draft editor"}
                </h3>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                  Edit the structured JSON fields directly. Validation persists the edited payload,
                  and publish prepares the Amazon-compatible document preview.
                </p>
                <div className="mt-4 rounded-[1.25rem] border border-amber-300/15 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
                  Publish preparation now resolves uploaded, generated, and selected library assets into
                  the Amazon payload when the module type supports them. Text-only modules still publish
                  without images, and unsupported module-image combinations are blocked before publish.
                </div>
                <div className="mt-4">
                  <AplusScoreBadge score={optimizationScore} />
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  ref={previewTriggerRef}
                  onClick={() => setIsPreviewOpen(true)}
                  disabled={!editorDraft}
                  className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm font-medium text-slate-100 transition hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <span className="inline-flex items-center gap-2">
                    <MonitorSmartphone className="h-4 w-4" />
                    Preview A+ layout
                  </span>
                </button>
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
                  disabled={
                    !selectedDraftId ||
                    isPublishing ||
                    hasUnsavedChanges ||
                    !publishReady
                  }
                  className="rounded-[1.25rem] bg-amber-300 px-4 py-3 text-sm font-medium text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isPublishing ? "Preparing..." : "Prepare publish payload"}
                </button>
              </div>
            </div>

              <div className="mt-5">
              <DraftMetadataBar
                draft={selectedDraft}
                product={selectedProduct}
                sourceLanguage={generationSourceLanguage}
                targetLanguage={generationTargetLanguage}
                autoTranslate={generationAutoTranslate}
                formatTimestamp={formatTimestamp}
              />
            </div>

            <div className="mt-5">
              <AplusReadinessPanel
                draft={selectedDraft}
                product={selectedProduct}
                hasUnsavedChanges={hasUnsavedChanges}
              />
            </div>

            <div className="mt-5">
              <AplusOptimizationPanel
                draft={selectedDraft}
                hasUnsavedChanges={hasUnsavedChanges}
              />
            </div>

            {!editorDraft ? (
              <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
                Generate a draft or select an existing draft to start editing the A+ payload.
              </div>
            ) : (
              <div className="mt-6 space-y-8">
                {(isGenerating || isValidating || isPublishing) ? (
                  <div className="flex items-center gap-3 rounded-[1.25rem] bg-white/[0.03] px-4 py-3 text-sm text-slate-300">
                    <LoaderCircle className="h-4 w-4 animate-spin text-sky-200" />
                    <span>
                      {isGenerating
                        ? autoTranslate
                          ? "Generating and translating structured A+ content..."
                          : "Generating structured A+ content..."
                          : isValidating
                            ? "Validating structured draft..."
                            : "Preparing Amazon-compatible publish payload..."}
                    </span>
                  </div>
                ) : null}

                {hasUnsavedChanges ? (
                  <div className="rounded-[1.25rem] border border-sky-300/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">
                    Editor changes are unsaved. Validate again to refresh the publish checklist and enable
                    publish preview.
                  </div>
                ) : null}

                {selectedDraft?.validated_payload ? (
                  <div className="rounded-[1.25rem] border border-white/10 bg-white/[0.03] px-4 py-3 text-sm leading-6 text-slate-300">
                    The last validated payload stays frozen as the editorial checkpoint. Background image
                    updates change the working draft only until you validate again.
                  </div>
                ) : null}

                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-white">Core message</p>
                    <p className="mt-1 text-sm text-slate-500">
                      Keep the opening proposition concise and easy to scan in a module-based layout.
                    </p>
                  </div>

                  <AplusSectionWarnings items={coreMessageSuggestions} />

                  <div className="grid gap-4 lg:grid-cols-2">
                    <label className="block space-y-2">
                      <span className="text-sm text-slate-300">Headline</span>
                      <p className="text-xs text-slate-500">Short, primary value proposition.</p>
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
                        className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3.5 text-base font-medium text-white outline-none"
                      />
                    </label>

                    <label className="block space-y-2">
                      <span className="text-sm text-slate-300">Subheadline</span>
                      <p className="text-xs text-slate-500">Support the main promise with one clear clarifier.</p>
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
                        className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3.5 text-base text-white outline-none"
                      />
                    </label>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium text-white">Brand story</p>
                    <p className="mt-1 text-sm text-slate-500">
                      Focus on differentiation, audience fit, and trust signals instead of generic claims.
                    </p>
                  </div>

                  <AplusSectionWarnings items={brandStorySuggestions} />

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
                      rows={6}
                      className="w-full rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-7 text-white outline-none"
                    />
                  </label>
                </div>

                <div className="grid gap-5 xl:grid-cols-2">
                  <div className="space-y-3 rounded-[1.5rem] bg-white/[0.03] p-4">
                    <AplusSectionWarnings items={featureSuggestions} />
                    <label className="block space-y-2">
                      <span className="text-sm font-medium text-white">Key features</span>
                      <p className="text-xs leading-5 text-slate-500">
                        One benefit-led point per line. These will be visible to editors and reused across modules.
                      </p>
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
                        className="w-full rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm leading-7 text-white outline-none"
                      />
                    </label>
                  </div>

                  <label className="block space-y-2 rounded-[1.5rem] bg-white/[0.03] p-4">
                    <span className="text-sm font-medium text-white">Compliance notes</span>
                    <p className="text-xs leading-5 text-slate-500">
                      Flag claims, references, or creative assumptions that need human review before publish.
                    </p>
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
                      className="w-full rounded-[1.25rem] border border-white/10 bg-slate-950/60 px-4 py-3 text-sm leading-7 text-white outline-none"
                    />
                  </label>
                </div>

                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">Content modules</p>
                      <p className="mt-1 text-sm text-slate-500">
                        Expand a module to edit its structure, or collapse it to scan the overall draft more quickly.
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="rounded-full border border-white/10 px-3 py-1.5 text-xs text-slate-300">
                        {editorDraft.modules.length} modules
                      </span>
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
                  </div>

                  <AplusSectionWarnings items={moduleSuggestions} />

                  <div className="space-y-4">
                    {editorDraft.modules.map((module, index) => (
                      <AplusModuleEditorCard
                        key={module.module_id}
                        index={index}
                        module={module}
                        isExpanded={expandedModules.includes(index)}
                        canRemove={editorDraft.modules.length > 3}
                        onToggle={() => toggleModule(index)}
                        onRemove={() => removeModule(index)}
                        onUpdate={(patch) => updateModule(index, patch)}
                        moduleLabels={moduleLabels}
                        assets={assets}
                        isLoadingAssets={isLoadingAssets}
                        isUploadingImage={imageUploadState[index]?.pending ?? false}
                        imageUploadError={imageUploadState[index]?.error ?? assetLibraryError}
                        onUploadImage={(file) => void handleModuleImageUpload(index, file)}
                        onSelectAsset={(asset) => attachExistingAsset(index, asset)}
                        onClearImage={() => clearModuleImage(index)}
                        canGenerateImage={Boolean(selectedDraftId) && !hasUnsavedChanges}
                        onGenerateImage={() => void handleGenerateModuleImage(index)}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </article>

          <section>
            <article className="rounded-[1.75rem] bg-slate-950/50 p-5 shadow-lg shadow-black/10 sm:p-6">
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
                  <div className="rounded-[1.25rem] border border-amber-300/15 bg-amber-500/10 px-4 py-3 text-sm leading-6 text-amber-100">
                    This payload reflects the current publish mapping, including resolved module images
                    where the module type supports them. Text-only modules continue to use the validated
                    <span className="mx-1 font-mono text-xs">imageBrief</span>
                    guidance without an embedded image object.
                  </div>
                  <pre className="overflow-x-auto rounded-[1.5rem] border border-white/10 bg-slate-950 px-4 py-4 text-xs leading-6 text-slate-200">
                    {JSON.stringify(publishResult.prepared_payload, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="mt-6 rounded-[1.5rem] border border-dashed border-white/10 bg-white/[0.03] p-6 text-sm leading-6 text-slate-400">
                  Prepare the publish payload to inspect the Amazon-compatible JSON that will be sent
                  by the backend publish workflow, including resolved module images when the module type
                  supports them.
                </div>
              )}
            </article>
          </section>
        </div>
      </section>

      {isPreviewOpen && editorDraft ? (
        <AplusPreviewModal
          draft={editorDraft}
          language={generationTargetLanguage}
          assets={assets}
          onClose={() => setIsPreviewOpen(false)}
          returnFocusTo={previewTriggerRef.current}
        />
      ) : null}
    </div>
  );
}
