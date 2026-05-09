export type TabId =
  | "today"
  | "seeds"
  | "sprout"
  | "write"
  | "history"
  | "profile"
  | "onboarding";

export type InputCategoryKind = "interest" | "following" | "serendipity";

export interface InputCategory {
  id: string;
  name: string;
  meta: string;
  kind: InputCategoryKind;
  active?: boolean;
  available?: boolean;
}

export interface ContentSource {
  sourceType: string;
  title: string;
  meta: string[];
  rawExcerpt: string;
  contribution: string;
}

export interface WorthReadingCard {
  id: string;
  categoryId: string;
  tags: { label: string; tone: "blue" | "green" | "orange" | "purple" | "red" }[];
  title: string;
  recommendationReason: string;
  contentSummary: string;
  controversies: string[];
  writingAngles: string[];
  originalSources?: ContentSource[];
  featured?: boolean;
}

export interface IdeaSeed {
  id: string;
  title: string;
  interestName: string;
  statusLabel: string;
  statusTone: "green" | "orange" | "blue" | "purple";
  source: string;
  sourceSummary: string;
  userReaction: string;
  coreClaim: string;
  possibleAngles: string[];
  requiredMaterials: string[];
}

export interface SproutOpportunity {
  id: string;
  score: number;
  tags: { label: string; tone: "blue" | "green" | "orange" | "purple" }[];
  activatedSeed: string;
  triggerTopic: string;
  whyWorthWriting: string;
  suggestedTitle: string;
  suggestedAngle: string;
  suggestedMaterials: string;
}

export interface MemorySummary {
  interestName: string;
  knowledgeLevel: string;
  preferredPerspective: string[];
  evidencePreference: string;
  writingReminder: string;
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
  status: string;
  statusTone: "green" | "orange" | "blue";
  performanceSummary: string;
  commentInsights: string[];
  memoryAction: string;
  metrics: { label: string; value: number }[];
}

export interface MockBootstrap {
  profile: ProfileData;
  categories: InputCategory[];
  cards: WorthReadingCard[];
  seeds: IdeaSeed[];
  sproutOpportunities: SproutOpportunity[];
  feedbackArticles: FeedbackArticle[];
}
