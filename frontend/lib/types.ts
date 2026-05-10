export type TabId =
  | "today"
  | "seeds"
  | "sprout"
  | "write"
  | "history"
  | "profile"
  | "onboarding";

export type Tone = "blue" | "green" | "orange" | "purple" | "red";

export type InputCategoryKind = "interest" | "following" | "serendipity";

export interface InputCategory {
  id: string;
  name: string;
  meta: string;
  kind: InputCategoryKind;
  active?: boolean;
}

export interface ContentSource {
  sourceId: string;
  sourceType: string;
  sourceUrl?: string;
  title: string;
  author?: string;
  publishedAt?: string;
  authorityMeta?: string;
  meta: string[];
  rawExcerpt: string;
  fullContent: string;
  contribution: string;
}

export interface WorthReadingCard {
  id: string;
  categoryId: string;
  tags: { label: string; tone: Tone }[];
  title: string;
  recommendationReason: string;
  contentSummary: string;
  controversies: string[];
  writingAngles: string[];
  originalSources: ContentSource[];
  relevanceScore: number;
  authorityScore?: number;
  popularityScore?: number;
  controversyScore?: number;
  createdAt: string;
  featured?: boolean;
}

export type SeedReaction =
  | "agree"
  | "disagree"
  | "question"
  | "supplement"
  | "want_to_write"
  | "manual";

export type SeedStatus =
  | "dormant"
  | "water_needed"
  | "sproutable"
  | "high_timeliness"
  | "writing"
  | "published"
  | "expired";

export type WateringMaterialType =
  | "evidence"
  | "counterargument"
  | "personal_experience"
  | "open_question";

export interface WateringMaterial {
  id: string;
  type: WateringMaterialType;
  title: string;
  content: string;
  sourceLabel?: string;
  adopted: boolean;
  createdAt: string;
}

export interface SeedQuestion {
  id: string;
  question: string;
  agentAnswer: string;
  citedSourceIds: string[];
  status: "answered" | "resolved" | "needs_material";
  createdAt: string;
}

export interface IdeaSeed {
  id: string;
  interestId: string;
  title: string;
  interestName: string;
  source: string;
  sourceTitle: string;
  sourceSummary: string;
  sourceUrl?: string;
  sourceType: string;
  userReaction: SeedReaction;
  userNote: string;
  coreClaim: string;
  possibleAngles: string[];
  counterArguments: string[];
  requiredMaterials: string[];
  wateringMaterials: WateringMaterial[];
  questions: SeedQuestion[];
  status: SeedStatus;
  maturityScore: number;
  activationScore?: number;
  createdFromCardId?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SproutOpportunity {
  id: string;
  seedId: string;
  interestId: string;
  score: number;
  tags: { label: string; tone: Tone }[];
  activatedSeed: string;
  triggerTopic: string;
  whyWorthWriting: string;
  suggestedTitle: string;
  suggestedAngle: string;
  suggestedMaterials: string;
  status?: "new" | "supplemented" | "angle_changed" | "dismissed" | "writing";
}

export interface MemorySummary {
  interestId: string;
  interestName: string;
  knowledgeLevel: string;
  preferredPerspective: string[];
  evidencePreference: string;
  writingReminder: string;
  feedbackSummary?: string;
}

export interface ProfileData {
  nickname: string;
  accountStatus: string;
  role: string;
  interests: string[];
  avoidances: string;
  globalMemory: {
    longTermBackground: string;
    contentPreference: string;
    writingStyle: string;
    recommendationStrategy: string;
    riskReminder: string;
  };
  interestMemories: MemorySummary[];
}

export interface FeedbackArticle {
  id: string;
  title: string;
  interestId: string;
  linkedSeedId?: string;
  status: string;
  statusTone: "green" | "orange" | "blue";
  performanceSummary: string;
  commentInsights: string[];
  memoryAction: string;
  metrics: { label: string; value: number }[];
}

export interface WritingSession {
  sessionId: string;
  seedId: string;
  interestId: string;
  articleType: string;
  coreClaim: string;
  tone: "balanced" | "sharp" | "steady";
  confirmed: boolean;
  adoptedSuggestions: string[];
  draftStatus: "claim_confirming" | "blueprint_ready" | "draft_ready" | "reviewing" | "finalized" | "published";
  savedDraft: boolean;
  publishedArticleId?: string;
}

export interface CategoryRefreshState {
  refreshCount: number;
  refreshedAt: string;
  visibleCardIds: string[];
}

export interface DemoState {
  hasEntered: boolean;
  activeTab: TabId;
  selectedCategoryId: string;
  selectedSeedId: string;
  profile: ProfileData;
  categories: InputCategory[];
  cards: WorthReadingCard[];
  seeds: IdeaSeed[];
  sproutOpportunities: SproutOpportunity[];
  feedbackArticles: FeedbackArticle[];
  reactions: Record<string, SeedReaction>;
  expandedCardIds: string[];
  expandedSourceIds: Record<string, string>;
  categoryRefreshState: Record<string, CategoryRefreshState>;
  sproutStarted: boolean;
  writingSession?: WritingSession;
}

export interface MockBootstrap {
  profile: ProfileData;
  categories: InputCategory[];
  cards: WorthReadingCard[];
  seeds: IdeaSeed[];
  sproutOpportunities: SproutOpportunity[];
  feedbackArticles: FeedbackArticle[];
}
