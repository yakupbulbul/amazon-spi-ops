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
