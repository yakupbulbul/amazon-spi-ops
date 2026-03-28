export type HealthResponse = {
  status: string;
  service: string;
};

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

export type DashboardMetric = {
  label: string;
  value: number;
  note: string;
};

export type DashboardActivity = {
  title: string;
  detail: string;
  occurred_at: string;
};

export type DashboardAlert = {
  title: string;
  detail: string;
  severity: string;
  occurred_at: string;
};

export type SlackDeliveryItem = {
  notification_type: string;
  status: string;
  message_preview: string;
  created_at: string;
};

export type DashboardSummaryResponse = {
  metrics: DashboardMetric[];
  recent_activity: DashboardActivity[];
  inventory_alerts: DashboardAlert[];
  slack_delivery: SlackDeliveryItem[];
};

export type ProductInventorySummary = {
  available_quantity: number;
  reserved_quantity: number;
  inbound_quantity: number;
  alert_status: string;
};

export type ProductListItem = {
  id: string;
  sku: string;
  asin: string;
  title: string;
  brand: string | null;
  source: string;
  marketplace_id: string;
  price_amount: string | null;
  price_currency: string | null;
  low_stock_threshold: number;
  is_active: boolean;
  inventory: ProductInventorySummary | null;
};

export type ProductListResponse = {
  items: ProductListItem[];
};

export type ProductMutationResponse = {
  product_id: string;
  status: string;
  message: string;
  updated_at: string;
};

export type CatalogImportJob = {
  id: string;
  status: string;
  source: string;
  marketplace_id: string;
  created_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
  processed_count: number;
  total_expected: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
};

export type InventoryItem = {
  product_id: string;
  sku: string;
  asin: string;
  product_name: string;
  marketplace_id: string;
  available_quantity: number;
  reserved_quantity: number;
  inbound_quantity: number;
  low_stock_threshold: number;
  alert_status: string;
  captured_at: string | null;
};

export type InventoryListResponse = {
  items: InventoryItem[];
};

export type InventoryAlertItem = {
  product_id: string;
  sku: string;
  product_name: string;
  severity: string;
  message: string;
  available_quantity: number;
  low_stock_threshold: number;
  created_at: string;
};

export type InventoryAlertListResponse = {
  items: InventoryAlertItem[];
};

export type InventorySyncResponse = {
  status: string;
  source: string;
  synced_count: number;
  synced_at: string;
};

export type AplusModulePayload = {
  module_type: "hero" | "feature" | "comparison" | "faq";
  headline: string;
  body: string;
  bullets: string[];
  image_brief: string;
};

export type AplusDraftPayload = {
  headline: string;
  subheadline: string;
  brand_story: string;
  key_features: string[];
  modules: AplusModulePayload[];
  compliance_notes: string[];
};

export type AplusDraftResponse = {
  id: string;
  product_id: string;
  product_sku: string;
  product_asin: string;
  product_title: string;
  marketplace_id: string;
  status: string;
  brand_tone: string | null;
  positioning: string | null;
  draft_payload: AplusDraftPayload;
  validated_payload: AplusDraftPayload | null;
  created_at: string;
  updated_at: string;
};

export type AplusDraftListResponse = {
  items: AplusDraftResponse[];
};

export type AplusPublishResponse = {
  draft: AplusDraftResponse;
  publish_job_id: string;
  status: string;
  message: string;
  prepared_payload: Record<string, unknown>;
};

export type SlackNotificationLog = {
  id: string;
  notification_type: string;
  status: string;
  channel_label: string | null;
  message_preview: string;
  error_message: string | null;
  created_at: string;
};

export type EventLogItem = {
  id: string;
  event_type: string;
  source: string;
  status: string;
  payload: Record<string, unknown>;
  occurred_at: string;
  notifications: SlackNotificationLog[];
};

export type EventListResponse = {
  items: EventLogItem[];
};

export type SlackTestResponse = {
  event_id: string;
  notification_id: string;
  status: string;
  message: string;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parsing errors and keep the default message
    }
    throw new Error(detail);
  }

  return (await response.json()) as T;
}

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  });
}

export async function getCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>("/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getDashboardSummary(token: string): Promise<DashboardSummaryResponse> {
  return apiRequest<DashboardSummaryResponse>("/dashboard/summary", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getProducts(token: string): Promise<ProductListResponse> {
  return apiRequest<ProductListResponse>("/products", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function createCatalogImportJob(token: string): Promise<CatalogImportJob> {
  return apiRequest<CatalogImportJob>("/products/import", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getLatestCatalogImportJob(
  token: string,
): Promise<CatalogImportJob | null> {
  return apiRequest<CatalogImportJob | null>("/products/import-jobs/latest", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function updateProductPrice(
  token: string,
  productId: string,
  payload: { price_amount: string; price_currency: string },
): Promise<ProductMutationResponse> {
  return apiRequest<ProductMutationResponse>(`/products/${productId}/price`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function updateProductStock(
  token: string,
  productId: string,
  payload: { quantity: number },
): Promise<ProductMutationResponse> {
  return apiRequest<ProductMutationResponse>(`/products/${productId}/stock`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function getAplusDrafts(token: string): Promise<AplusDraftListResponse> {
  return apiRequest<AplusDraftListResponse>("/aplus/drafts", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function generateAplusDraft(
  token: string,
  payload: { product_id: string; brand_tone?: string; positioning?: string },
): Promise<AplusDraftResponse> {
  return apiRequest<AplusDraftResponse>("/aplus/generate", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function validateAplusDraft(
  token: string,
  payload: { draft_id: string; draft_payload: AplusDraftPayload },
): Promise<AplusDraftResponse> {
  return apiRequest<AplusDraftResponse>("/aplus/validate", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function publishAplusDraft(
  token: string,
  draftId: string,
): Promise<AplusPublishResponse> {
  return apiRequest<AplusPublishResponse>("/aplus/publish", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ draft_id: draftId }),
  });
}

export async function getEvents(token: string): Promise<EventListResponse> {
  return apiRequest<EventListResponse>("/events", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function sendSlackTestNotification(token: string): Promise<SlackTestResponse> {
  return apiRequest<SlackTestResponse>("/notifications/slack/test", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInventory(token: string): Promise<InventoryListResponse> {
  return apiRequest<InventoryListResponse>("/inventory", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getInventoryAlerts(token: string): Promise<InventoryAlertListResponse> {
  return apiRequest<InventoryAlertListResponse>("/inventory/alerts", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function syncInventory(token: string): Promise<InventorySyncResponse> {
  return apiRequest<InventorySyncResponse>("/inventory/sync", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}
