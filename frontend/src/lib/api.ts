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
