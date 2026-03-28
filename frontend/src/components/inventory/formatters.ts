const relativeTimeFormatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

const marketplaceLabels: Record<string, string> = {
  A1PA6795UKMFR9: "Amazon.de",
  A1F83G8C2ARO7P: "Amazon.co.uk",
  ATVPDKIKX0DER: "Amazon.com",
};

export function formatStatusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function formatQuantity(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatAbsoluteTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatRelativeTimestamp(value: string | null): string {
  if (!value) {
    return "Not synced";
  }

  const timestamp = new Date(value);
  const diffInSeconds = Math.round((timestamp.getTime() - Date.now()) / 1000);
  const absoluteSeconds = Math.abs(diffInSeconds);

  if (absoluteSeconds < 60) {
    return "Just now";
  }

  if (absoluteSeconds < 3600) {
    return relativeTimeFormatter.format(Math.round(diffInSeconds / 60), "minute");
  }

  if (absoluteSeconds < 86400) {
    return relativeTimeFormatter.format(Math.round(diffInSeconds / 3600), "hour");
  }

  return relativeTimeFormatter.format(Math.round(diffInSeconds / 86400), "day");
}

export function formatMarketplaceLabel(marketplaceId: string): string {
  return marketplaceLabels[marketplaceId] ?? `Marketplace ${marketplaceId}`;
}
