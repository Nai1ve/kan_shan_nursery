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
  MemorySummary,
  ProfileData,
  SeedQuestion,
  SeedReaction,
  SproutOpportunity,
  WateringMaterial,
  WateringMaterialType,
  WorthReadingCard,
} from "./types";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_KANSHAN_GATEWAY_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const SESSION_KEY = "kanshan:session:v1";
export const KANSHAN_LLM_NOTICE_EVENT = "kanshan:llm-notice";

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  const session = window.localStorage.getItem(SESSION_KEY);
  if (!session) return null;
  try {
    const parsed = JSON.parse(session);
    return parsed.sessionId || null;
  } catch {
    return null;
  }
}

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

interface GatewayNotice {
  code?: string;
  level?: string;
  message?: string;
}

function isErrorEnvelope(body: unknown): body is ErrorEnvelope {
  return typeof body === "object" && body !== null && "error" in body;
}

export function dispatchGatewayNotices(body: unknown): void {
  if (typeof window === "undefined" || typeof body !== "object" || body === null) return;
  const envelope = body as { data?: { notices?: GatewayNotice[] }; meta?: { notices?: GatewayNotice[] } };
  const notices = envelope.data?.notices ?? envelope.meta?.notices ?? [];
  notices
    .filter((notice) => notice.code === "USER_LLM_PROVIDER_FAILED" && notice.message)
    .forEach((notice) => {
      window.dispatchEvent(new CustomEvent(KANSHAN_LLM_NOTICE_EVENT, { detail: notice }));
    });
}

async function request<T>(method: string, path: string, payload?: unknown): Promise<T> {
  const url = `${GATEWAY_URL}${path}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const sessionId = getSessionId();
  if (sessionId) headers["x-session-id"] = sessionId;

  const init: RequestInit = { method, headers, cache: "no-store" };
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
  dispatchGatewayNotices(body);
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

export async function gatewayFetchContentCards(
  categoryId?: string,
  options?: { limit?: number; excludeIds?: string[] },
): Promise<WorthReadingCard[]> {
  const params = new URLSearchParams();
  if (categoryId) params.set("categoryId", categoryId);
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.excludeIds?.length) params.set("excludeIds", options.excludeIds.join(","));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const body = await request<{ items?: WorthReadingCard[]; cards?: WorthReadingCard[] }>(
    "GET",
    `/api/v1/content/cards${suffix}`,
  );
  return body.items ?? body.cards ?? [];
}

export async function gatewayRefreshCategory(
  categoryId: string,
  payload?: { limit?: number; excludeIds?: string[] },
): Promise<{
  categoryId: string;
  refreshState?: { refreshCount: number; refreshedAt: string; source?: string };
  cards: WorthReadingCard[];
}> {
  return request<{
    categoryId: string;
    refreshState?: { refreshCount: number; refreshedAt: string; source?: string };
    cards: WorthReadingCard[];
  }>("POST", `/api/v1/content/categories/${encodeURIComponent(categoryId)}/refresh`, {
    limit: payload?.limit,
    exclude_ids: payload?.excludeIds ?? [],
  });
}

export async function gatewayEnrichCard(cardId: string): Promise<WorthReadingCard> {
  return request<WorthReadingCard>("POST", `/api/v1/content/cards/${encodeURIComponent(cardId)}/enrich`);
}

export async function gatewayFetchCategories(): Promise<InputCategory[]> {
  return request<InputCategory[]>("GET", "/api/v1/categories");
}

export async function gatewayFetchProfileInterests(): Promise<MemorySummary[]> {
  return request<MemorySummary[]>("GET", "/api/v1/profile/interests");
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

export async function gatewayCreateSeedFromCard(payload: {
  cardId: string;
  reaction: Extract<SeedReaction, "agree" | "disagree" | "question">;
  userNote?: string;
  card?: WorthReadingCard;
  seedId?: string;
}): Promise<IdeaSeed> {
  return request<IdeaSeed>("POST", "/api/v1/seeds/from-card", payload);
}

export async function gatewayCreateManualSeed(payload: Partial<IdeaSeed>): Promise<IdeaSeed> {
  return request<IdeaSeed>("POST", "/api/v1/seeds", payload);
}

export async function gatewayUpdateSeed(seedId: string, patch: Partial<IdeaSeed>): Promise<IdeaSeed> {
  return request<IdeaSeed>("PATCH", `/api/v1/seeds/${encodeURIComponent(seedId)}`, patch);
}

export async function gatewayAddSeedQuestion(
  seedId: string,
  payload: { question: string; parentQuestionId?: string },
): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "POST",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/questions`,
    payload,
  );
}

export async function gatewayMarkSeedQuestion(
  seedId: string,
  questionId: string,
  status: SeedQuestion["status"],
): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "PATCH",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/questions/${encodeURIComponent(questionId)}`,
    { status },
  );
}

export async function gatewayAddSeedMaterial(
  seedId: string,
  payload: { type: WateringMaterialType; title: string; content: string; sourceLabel?: string; adopted?: boolean },
): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "POST",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/materials`,
    payload,
  );
}

export async function gatewayUpdateSeedMaterial(
  seedId: string,
  materialId: string,
  patch: Partial<WateringMaterial>,
): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "PATCH",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/materials/${encodeURIComponent(materialId)}`,
    patch,
  );
}

export async function gatewayDeleteSeedMaterial(seedId: string, materialId: string): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "DELETE",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/materials/${encodeURIComponent(materialId)}`,
  );
}

export async function gatewayAgentSupplementSeed(
  seedId: string,
  payload: { type: Extract<WateringMaterialType, "evidence" | "counterargument"> },
): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "POST",
    `/api/v1/seeds/${encodeURIComponent(seedId)}/materials/agent-supplement`,
    payload,
  );
}

export async function gatewayMergeSeeds(targetSeedId: string, sourceSeedId: string): Promise<IdeaSeed> {
  return request<IdeaSeed>(
    "POST",
    `/api/v1/seeds/${encodeURIComponent(targetSeedId)}/merge`,
    { sourceSeedId },
  );
}
