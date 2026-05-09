import type {
  FeedbackArticle,
  IdeaSeed,
  InputCategory,
  ProfileData,
  SproutOpportunity,
  WorthReadingCard,
} from "./types";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Mock API failed: ${response.status} ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function fetchProfile(): Promise<ProfileData> {
  return getJson<ProfileData>("/api/mock/profile");
}

export async function fetchContent(): Promise<{
  categories: InputCategory[];
  cards: WorthReadingCard[];
}> {
  return getJson("/api/mock/content");
}

export async function fetchSeeds(): Promise<IdeaSeed[]> {
  return getJson<IdeaSeed[]>("/api/mock/seeds");
}

export async function fetchSproutOpportunities(): Promise<SproutOpportunity[]> {
  return getJson<SproutOpportunity[]>("/api/mock/sprout");
}

export async function fetchFeedbackArticles(): Promise<FeedbackArticle[]> {
  return getJson<FeedbackArticle[]>("/api/mock/feedback");
}
