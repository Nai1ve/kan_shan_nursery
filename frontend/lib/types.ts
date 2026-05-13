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
  description?: string;
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
  enriched?: boolean;
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
  userId?: string;
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
  runId?: string;
  userId?: string;
  seedId: string;
  interestId: string;
  triggerType?: "hot" | "today_card" | "following" | "search";
  triggerCardIds?: string[];
  triggerTopic: string;
  activatedSeed: string;
  whyWorthWriting: string;
  suggestedTitle: string;
  suggestedAngle: string;
  suggestedMaterials: string;
  missingMaterials?: string[];
  previousAngles?: { title: string; angle: string }[];
  score: number;
  tags: { label: string; tone: Tone }[];
  status?: "active" | "new" | "supplemented" | "angle_changed" | "dismissed" | "writing";
  createdAt?: string;
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
  memoryOverride?: MemorySummary;
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

// Auth types
export type AuthStatus = "guest" | "registered" | "authenticated" | "logged_out";

export type ZhihuBindingStatus =
  | "not_started"
  | "authorizing"
  | "bound"
  | "failed"
  | "skipped"
  | "unavailable"
  | "expired";

export type OnboardingStatus =
  | "not_started"
  | "preferences_pending"
  | "provisional_ready"
  | "completed";

export type ProfileGenerationStatus =
  | "not_started"
  | "queued"
  | "collecting_oauth_data"
  | "analyzing"
  | "draft_ready"
  | "applied"
  | "failed";

export interface EnrichmentJob {
  jobId: string | null;
  status: "not_started" | "queued" | "running" | "completed" | "failed" | "fallback";
  temporaryProfile?: ProfileData;
  signalCounts?: Record<string, number>;
  memoryUpdateRequestIds?: string[];
  errorMessage?: string;
}

export interface MemoryUpdateRequest {
  id: string;
  userId?: string;
  scope: "global" | "interest";
  interestId?: string;
  targetField: string;
  suggestedValue: string;
  reason: string;
  evidenceRefs?: string[];
  status: "pending" | "applied" | "rejected";
  createdAt: string;
}

export type UserSetupState =
  | "zhihu_pending"
  | "llm_pending"
  | "preferences_pending"
  | "provisional_ready"
  | "ready";

export interface CurrentUser {
  userId: string;
  nickname: string;
  email?: string;
  username?: string;
  createdAt: string;
}

export interface UserSession {
  sessionId: string;
  userId: string;
  createdAt: string;
  expiresAt: string;
}

export interface AuthMeResponse {
  authenticated: boolean;
  user: CurrentUser | null;
  setupState: UserSetupState | null;
}

export interface RegisterRequest {
  nickname: string;
  email?: string;
  username?: string;
  password: string;
}

export interface LoginRequest {
  identifier: string;
  password: string;
}

export interface AuthResponse {
  user: CurrentUser;
  session: UserSession;
  setupState: UserSetupState;
}

export interface ZhihuBindingViewModel {
  userId: string;
  zhihuUid: string | null;
  bindingStatus: ZhihuBindingStatus;
  boundAt: string | null;
  expiredAt: string | null;
}

export interface LlmQuotaViewModel {
  profileSignalSummarize: { used: number; limit: number; remaining?: number };
  profileMemorySynthesize: { used: number; limit: number; remaining?: number };
  profileRiskReview: { used: number; limit: number; remaining?: number };
  summarizeContent: { used: number; limit: number; remaining?: number };
  answerSeedQuestion: { used: number; limit: number; remaining?: number };
  supplementMaterial: { used: number; limit: number; remaining?: number };
  argumentBlueprint: { used: number; limit: number; remaining?: number };
  draft: { used: number; limit: number; remaining?: number };
  roundtableReview: { used: number; limit: number; remaining?: number };
}

export interface LlmConfigViewModel {
  status: "platform_free" | "user_configured" | "not_configured" | "invalid" | "quota_limited";
  activeProvider: "platform_free" | "user_provider" | "none";
  displayName?: string;
  maskedKey?: string;
  model?: string;
  quota?: LlmQuotaViewModel;
  errorMessage?: string;
}

export interface ZhihuExchangeTicketRequest {
  ticket: string;
}

export interface ZhihuExchangeTicketResponse {
  user: CurrentUser;
  session: UserSession;
  setupState: UserSetupState;
}

export interface ZhihuLoginTicketMessage {
  type: "zhihu-login-ticket";
  ticket: string;
  nonce: string;
  ts: number;
}

export interface UserSetupStateData {
  authStatus: AuthStatus;
  setupState: UserSetupState;
  zhihuBinding?: ZhihuBindingViewModel;
  llmConfig?: LlmConfigViewModel;
  profileGenerationStatus?: ProfileGenerationStatus;
}

export interface SelectedInterest {
  interestId: string;
  selected: boolean;
  selfRatedLevel: "beginner" | "intermediate" | "advanced";
  intent: "read" | "write" | "both";
}

export interface WritingStyleSurvey {
  logicDepth: 1 | 2 | 3 | 4 | 5;
  stanceSharpness: 1 | 2 | 3 | 4 | 5;
  personalExperienceWillingness: 1 | 2 | 3 | 4 | 5;
  expressionSharpness: 1 | 2 | 3 | 4 | 5;
  preferredFormat: "zhihu_answer" | "balanced" | "long_article" | "column" | "draft";
  evidenceVsJudgment: "evidence_first" | "balanced" | "judgment_first";
  wantsCounterArguments: boolean;
  openingStyle: "direct" | "balanced" | "story";
  titleStyle: "restrained" | "balanced" | "spreadable";
  uncertaintyTolerance: 1 | 2 | 3 | 4 | 5;
  emotionalTemperature: "cold" | "balanced" | "emotional";
  aiAssistanceBoundary: "outline" | "paragraph" | "draft" | "polish" | "publish_ready";
}

export interface OnboardingPayload {
  nickname: string;
  selectedInterests: SelectedInterest[];
  writingStyle: WritingStyleSurvey;
}

export interface OnboardingResponse {
  profile: ProfileData;
  profileStatus: "provisional";
  enrichmentJob?: {
    id: string;
    status: ProfileGenerationStatus;
  };
}
