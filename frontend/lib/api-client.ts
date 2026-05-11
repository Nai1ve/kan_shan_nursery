import type {
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  ProfileData,
  SproutOpportunity,
  WorthReadingCard,
} from "./types";
import {
  gatewayFetchContent,
  gatewayFetchFeedbackArticles,
  gatewayFetchProfile,
  gatewayFetchSeeds,
  gatewayFetchSproutOpportunities,
} from "./gateway-client";

/**
 * NEXT_PUBLIC_KANSHAN_BACKEND_MODE switches every page-level fetch:
 *   - "mock"    (default): Next.js /api/mock/* routes serve static fixtures.
 *   - "gateway": real api-gateway at :8000 with envelope unwrap + field shape.
 *
 * Frontend pages always import from this module so swapping modes is a
 * single env var, no per-page changes.
 */
const MODE = (process.env.NEXT_PUBLIC_KANSHAN_BACKEND_MODE || "mock").toLowerCase();
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

export const KANSHAN_BACKEND_MODE = USE_GATEWAY ? "gateway" : "mock";
