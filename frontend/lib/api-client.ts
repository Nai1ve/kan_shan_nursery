import type {
  EnrichmentJob,
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  ProfileData,
  SeedQuestion,
  SeedReaction,
  SproutOpportunity,
  WateringMaterial,
  WateringMaterialType,
  WorthReadingCard,
  MemorySummary,
} from "./types";
import {
  gatewayAddSeedMaterial,
  gatewayAddSeedQuestion,
  gatewayAgentSupplementSeed,
  gatewayCreateManualSeed,
  gatewayCreateSeedFromCard,
  gatewayDeleteSeedMaterial,
  gatewayEnrichCard,
  gatewayFetchCategories,
  gatewayFetchContent,
  gatewayFetchContentCards,
  gatewayFetchFeedbackArticles,
  gatewayFetchProfile,
  gatewayFetchProfileInterests,
  gatewayRefreshCategory,
  gatewayFetchSeeds,
  gatewayFetchSproutOpportunities,
  gatewayMarkSeedQuestion,
  gatewayMergeSeeds,
  gatewayUpdateSeed,
  gatewayUpdateSeedMaterial,
  dispatchGatewayNotices,
  KANSHAN_LLM_NOTICE_EVENT,
} from "./gateway-client";

export { KANSHAN_LLM_NOTICE_EVENT };

/**
 * NEXT_PUBLIC_KANSHAN_BACKEND_MODE switches every page-level fetch:
 *   - "mock"    (default): Next.js /api/mock/* routes serve static fixtures.
 *   - "gateway": real api-gateway at :8000 with envelope unwrap + field shape.
 *
 * Frontend pages always import from this module so swapping modes is a
 * single env var, no per-page changes.
 */
const MODE = (process.env.NEXT_PUBLIC_KANSHAN_BACKEND_MODE || "gateway").toLowerCase();
const USE_GATEWAY = MODE === "gateway";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Mock API failed: ${response.status} ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchProfile(): Promise<ProfileData> {
  return USE_GATEWAY ? gatewayFetchProfile() : getJson<ProfileData>("/api/mock/profile");
}

export async function fetchContent(): Promise<{
  categories: InputCategory[];
  cards: WorthReadingCard[];
}> {
  return USE_GATEWAY ? gatewayFetchContent() : getJson("/api/mock/content");
}

export async function fetchContentCards(
  categoryId?: string,
  options?: { limit?: number; excludeIds?: string[] },
): Promise<WorthReadingCard[]> {
  if (USE_GATEWAY) {
    return gatewayFetchContentCards(categoryId, options);
  }
  const query = categoryId ? `?categoryId=${encodeURIComponent(categoryId)}` : "";
  return getJson<WorthReadingCard[]>(`/api/mock/content/cards${query}`);
}

export async function refreshCategory(
  categoryId: string,
  options?: { limit?: number; excludeIds?: string[] },
): Promise<{
  categoryId: string;
  refreshState?: { refreshCount: number; refreshedAt: string; source?: string };
  cards: WorthReadingCard[];
}> {
  if (USE_GATEWAY) {
    return gatewayRefreshCategory(categoryId, options);
  }
  return getJson(`/api/mock/content/refresh/${encodeURIComponent(categoryId)}`);
}

export async function enrichCard(cardId: string): Promise<WorthReadingCard> {
  if (USE_GATEWAY) {
    return gatewayEnrichCard(cardId);
  }
  // Mock mode: return a dummy enriched card
  return getJson<WorthReadingCard>(`/api/mock/content/cards/${encodeURIComponent(cardId)}`);
}

export async function fetchCategories(): Promise<InputCategory[]> {
  return USE_GATEWAY ? gatewayFetchCategories() : getJson<InputCategory[]>("/api/mock/categories");
}

export async function fetchProfileInterests(): Promise<MemorySummary[]> {
  if (!USE_GATEWAY) return [];
  return gatewayFetchProfileInterests();
}

export async function fetchSeeds(): Promise<IdeaSeed[]> {
  return USE_GATEWAY ? gatewayFetchSeeds() : getJson<IdeaSeed[]>("/api/mock/seeds");
}

export async function fetchSproutOpportunities(): Promise<SproutOpportunity[]> {
  return USE_GATEWAY
    ? gatewayFetchSproutOpportunities()
    : getJson<SproutOpportunity[]>("/api/mock/sprout");
}

export async function fetchFeedbackArticles(): Promise<FeedbackArticle[]> {
  return USE_GATEWAY
    ? gatewayFetchFeedbackArticles()
    : getJson<FeedbackArticle[]>("/api/mock/feedback");
}

export async function createSeedFromCard(payload: {
  cardId: string;
  reaction: Extract<SeedReaction, "agree" | "disagree" | "question">;
  userNote?: string;
  card?: WorthReadingCard;
  seedId?: string;
}): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayCreateSeedFromCard(payload);
}

export async function createManualSeed(payload: Partial<IdeaSeed>): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayCreateManualSeed(payload);
}

export async function updateSeed(seedId: string, patch: Partial<IdeaSeed>): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayUpdateSeed(seedId, patch);
}

export async function addSeedQuestion(
  seedId: string,
  payload: { question: string; parentQuestionId?: string },
): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayAddSeedQuestion(seedId, payload);
}

export async function markSeedQuestion(
  seedId: string,
  questionId: string,
  status: SeedQuestion["status"],
): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayMarkSeedQuestion(seedId, questionId, status);
}

export async function addSeedMaterial(
  seedId: string,
  payload: { type: WateringMaterialType; title: string; content: string; sourceLabel?: string; adopted?: boolean },
): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayAddSeedMaterial(seedId, payload);
}

export async function updateSeedMaterial(
  seedId: string,
  materialId: string,
  patch: Partial<WateringMaterial>,
): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayUpdateSeedMaterial(seedId, materialId, patch);
}

export async function deleteSeedMaterial(seedId: string, materialId: string): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayDeleteSeedMaterial(seedId, materialId);
}

export async function agentSupplementSeed(
  seedId: string,
  payload: { type: Extract<WateringMaterialType, "evidence" | "counterargument"> },
): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayAgentSupplementSeed(seedId, payload);
}

export async function mergeSeedsApi(targetSeedId: string, sourceSeedId: string): Promise<IdeaSeed | null> {
  if (!USE_GATEWAY) return null;
  return gatewayMergeSeeds(targetSeedId, sourceSeedId);
}

export const KANSHAN_BACKEND_MODE = USE_GATEWAY ? "gateway" : "mock";

// Profile management API functions
export async function updateBasicProfile(data: Partial<ProfileData>): Promise<ProfileData> {
  if (!USE_GATEWAY) {
    throw new Error("updateBasicProfile only available in gateway mode");
  }
  return gatewayRequest<ProfileData>("PUT", "/profiles/me/basic", data);
}

export async function updateInterests(interests: Array<{ interestId: string; selected: boolean; selfRatedLevel: string; intent: string }>): Promise<ProfileData> {
  if (!USE_GATEWAY) {
    throw new Error("updateInterests only available in gateway mode");
  }
  return gatewayRequest<ProfileData>("PUT", "/profiles/me/interests", { interests });
}

export async function getWritingStyle(): Promise<Record<string, unknown>> {
  if (!USE_GATEWAY) {
    throw new Error("getWritingStyle only available in gateway mode");
  }
  return gatewayRequest<Record<string, unknown>>("GET", "/profiles/me/writing-style");
}

export async function updateWritingStyle(style: Record<string, unknown>): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("updateWritingStyle only available in gateway mode");
  }
  await gatewayRequest<void>("PUT", "/profiles/me/writing-style", style);
}

export async function getLLMConfig(): Promise<Record<string, unknown>> {
  if (!USE_GATEWAY) {
    throw new Error("getLLMConfig only available in gateway mode");
  }
  return gatewayRequest<Record<string, unknown>>("GET", "/llm/config/me");
}

export async function getLLMQuota(): Promise<Record<string, { used: number; limit: number; remaining: number }>> {
  if (!USE_GATEWAY) {
    throw new Error("getLLMQuota only available in gateway mode");
  }
  const resp = await gatewayRequest<{ platform: Record<string, { used: number; limit: number; remaining: number }> }>("GET", "/llm/quota/me");
  return resp.platform;
}

export async function updateLLMConfig(config: Record<string, unknown>): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("updateLLMConfig only available in gateway mode");
  }
  await gatewayRequest<void>("PUT", "/llm/config/me", config);
}

export async function updateGlobalMemory(memory: Record<string, unknown>): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("updateGlobalMemory only available in gateway mode");
  }
  await gatewayRequest<void>("PUT", "/memory/me/global", memory);
}

export async function updateInterestMemory(interestId: string, memory: Record<string, unknown>): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("updateInterestMemory only available in gateway mode");
  }
  await gatewayRequest<void>("PUT", `/memory/me/interests/${interestId}`, memory);
}

export async function getMemoryUpdateRequests(): Promise<Array<Record<string, unknown>>> {
  if (!USE_GATEWAY) {
    throw new Error("getMemoryUpdateRequests only available in gateway mode");
  }
  return gatewayRequest<Array<Record<string, unknown>>>("GET", "/memory/update-requests");
}

export async function applyMemoryUpdate(requestId: string): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("applyMemoryUpdate only available in gateway mode");
  }
  await gatewayRequest<void>("POST", `/memory/update-requests/${requestId}/apply`);
}

export async function rejectMemoryUpdate(requestId: string): Promise<void> {
  if (!USE_GATEWAY) {
    throw new Error("rejectMemoryUpdate only available in gateway mode");
  }
  await gatewayRequest<void>("POST", `/memory/update-requests/${requestId}/reject`);
}

// Helper function for gateway requests
async function gatewayRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const gatewayUrl = process.env.NEXT_PUBLIC_KANSHAN_GATEWAY_URL || "http://127.0.0.1:8000";
  const sessionRaw = typeof window !== "undefined" ? localStorage.getItem("kanshan:session:v1") : null;

  let sessionId: string | null = null;
  if (sessionRaw) {
    try {
      sessionId = JSON.parse(sessionRaw).sessionId || null;
    } catch {
      sessionId = null;
    }
  }

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (sessionId) {
    headers["x-session-id"] = sessionId;
  }

  const response = await fetch(`${gatewayUrl}/api/v1${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.detail?.message || error.message || `Request failed: ${response.status}`);
  }

  const data = await response.json();
  dispatchGatewayNotices(data);
  return data.data || data;
}

// Enrichment job API functions
export async function createEnrichmentJob(
  trigger: string = "oauth_bound",
  includeSources: string[] = ["zhihu_user", "followed", "followers", "moments"],
): Promise<{ jobId: string; status: string; temporaryProfileReady: boolean }> {
  if (!USE_GATEWAY) {
    throw new Error("createEnrichmentJob only available in gateway mode");
  }
  return gatewayRequest("POST", "/profile/enrichment-jobs", { trigger, includeSources });
}

export async function getLatestEnrichmentJob(): Promise<EnrichmentJob> {
  if (!USE_GATEWAY) {
    throw new Error("getLatestEnrichmentJob only available in gateway mode");
  }
  return gatewayRequest("GET", "/profile/enrichment-jobs/latest");
}
