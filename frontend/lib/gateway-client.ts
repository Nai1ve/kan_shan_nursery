/**
 * Gateway-backed API client.
 *
 * All requests hit `api-gateway` at NEXT_PUBLIC_KANSHAN_GATEWAY_URL (default
 * http://127.0.0.1:8000). The gateway wraps every success in
 * `{ request_id, data, meta }` and every failure in
 * `{ request_id, error: { code, message, detail } }`. This module peels the
 * envelope so callers only see the data they asked for, and converts
 * errors into native Error objects carrying the gateway code.
 */

import type {
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  ProfileData,
  SproutOpportunity,
  WorthReadingCard,
} from "./types";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_KANSHAN_GATEWAY_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

export class GatewayError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
    public readonly requestId?: string,
  ) {
    super(message);
    this.name = "GatewayError";
  }
}

interface SuccessEnvelope<T> {
  request_id: string;
  data: T;
  meta?: Record<string, unknown>;
}

interface ErrorEnvelope {
  request_id: string;
  error: { code: string; message: string; detail?: unknown };
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  return typeof body === "object" && body !== null && "error" in body;
}

async function request<T>(method: string, path: string, payload?: unknown): Promise<T> {
  const url = `${GATEWAY_URL}${path}`;
  const init: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
  };
  if (payload !== undefined) {
    init.body = JSON.stringify(payload);
  }
  const response = await fetch(url, init);
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    throw new GatewayError("INVALID_RESPONSE", `Invalid JSON from gateway ${path}`, response.status);
  }
  if (!response.ok || isErrorEnvelope(body)) {
    const err = isErrorEnvelope(body) ? body.error : null;
    throw new GatewayError(
      err?.code ?? "DOWNSTREAM_ERROR",
      err?.message ?? `${method} ${path} failed (${response.status})`,
      response.status,
      err?.detail,
      isErrorEnvelope(body) ? body.request_id : undefined,
    );
  }
  return (body as SuccessEnvelope<T>).data;
}

export async function gatewayFetchProfile(): Promise<ProfileData> {
  return request<ProfileData>("GET", "/api/v1/profile/me");
}

export async function gatewayFetchContent(): Promise<{
  categories: InputCategory[];
  cards: WorthReadingCard[];
}> {
  return request<{ categories: InputCategory[]; cards: WorthReadingCard[] }>(
    "GET",
    "/api/v1/content",
  );
}

export async function gatewayFetchSeeds(): Promise<IdeaSeed[]> {
  const body = await request<{ items: IdeaSeed[] }>("GET", "/api/v1/seeds");
  return body.items ?? [];
}

export async function gatewayFetchSproutOpportunities(): Promise<SproutOpportunity[]> {
  const body = await request<{ items: SproutOpportunity[] }>("GET", "/api/v1/sprout/opportunities");
  return body.items ?? [];
}

export async function gatewayFetchFeedbackArticles(): Promise<FeedbackArticle[]> {
  const body = await request<{ items: FeedbackArticle[] }>("GET", "/api/v1/feedback/articles");
  return body.items ?? [];
}
