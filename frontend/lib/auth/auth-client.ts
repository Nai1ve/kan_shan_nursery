/**
 * Auth API client with mock/gateway dual mode support.
 *
 * The mock mode is deliberately stateful through localStorage so the frontend
 * onboarding flow behaves like a real user system during demo development.
 */

import type {
  AuthMeResponse,
  AuthResponse,
  LoginRequest,
  MemorySummary,
  OnboardingPayload,
  OnboardingResponse,
  ProfileData,
  RegisterRequest,
  UserSetupState,
  UserSetupStateData,
  ZhihuExchangeTicketResponse,
  ZhihuBindingViewModel,
} from "@/lib/types";

const MODE = (process.env.NEXT_PUBLIC_KANSHAN_BACKEND_MODE || "gateway").toLowerCase();
const USE_GATEWAY = MODE === "gateway";

const GATEWAY_URL =
  process.env.NEXT_PUBLIC_KANSHAN_GATEWAY_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const SESSION_KEY = "kanshan:session:v1";
const MOCK_STORE_KEY = "kanshan:auth:mock-store:v1";

interface MockStore {
  users: Record<string, { user: AuthResponse["user"]; passwordHash: string }>;
  sessions: Record<string, string>;
  zhihuBindings: Record<string, ZhihuBindingViewModel>;
  onboarding: Record<string, OnboardingResponse>;
}

const interestNames: Record<string, string> = {
  shuma: "数码科技",
  zhichang: "职场教育",
  chuangzuo: "创作表达",
  shenghuo: "生活方式",
  shehui: "社会人文",
  bendi: "本地城市",
  yule: "文娱体育",
  caijing: "财经商业",
  jiankang: "健康医学",
  qiche: "汽车出行",
  lishi: "历史考古",
  huanjing: "环境自然",
};

function getSessionId(): string | null {
  if (typeof window === "undefined") return null;
  const session = localStorage.getItem(SESSION_KEY);
  if (!session) return null;
  try {
    const parsed = JSON.parse(session);
    return parsed.sessionId || null;
  } catch {
    return null;
  }
}

function shouldUseSameOriginGateway(): boolean {
  if (typeof window === "undefined") return false;
  if (!window.location.hostname.endsWith(".trycloudflare.com")) return false;
  try {
    const gateway = new URL(GATEWAY_URL);
    return gateway.hostname === "127.0.0.1" || gateway.hostname === "localhost";
  } catch {
    return false;
  }
}

function getGatewayBaseUrl(): string {
  return shouldUseSameOriginGateway() ? "" : GATEWAY_URL;
}

function saveSession(sessionId: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SESSION_KEY, JSON.stringify({ sessionId, savedAt: Date.now() }));
}

function clearSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(SESSION_KEY);
}

function emptyStore(): MockStore {
  return { users: {}, sessions: {}, zhihuBindings: {}, onboarding: {} };
}

function readStore(): MockStore {
  if (typeof window === "undefined") return emptyStore();
  const raw = localStorage.getItem(MOCK_STORE_KEY);
  if (!raw) return emptyStore();
  try {
    const parsed = JSON.parse(raw) as Partial<MockStore>;
    return {
      users: parsed.users || {},
      sessions: parsed.sessions || {},
      zhihuBindings: parsed.zhihuBindings || {},
      onboarding: parsed.onboarding || {},
    };
  } catch {
    return emptyStore();
  }
}

function writeStore(store: MockStore): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(MOCK_STORE_KEY, JSON.stringify(store));
}

function createId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
}

function currentUserId(store = readStore()): string | null {
  const sessionId = getSessionId();
  if (!sessionId) return null;
  return store.sessions[sessionId] || null;
}

function setupStateForUser(store: MockStore, userId: string): UserSetupState {
  if (store.onboarding[userId]) return "ready";
  return "zhihu_pending";
}

function createMockUser(nickname: string, password: string, email?: string, username?: string) {
  const store = readStore();
  const normalizedEmail = email?.trim() || undefined;
  const normalizedUsername = username?.trim() || undefined;

  if (normalizedEmail && Object.values(store.users).some(({ user }) => user.email === normalizedEmail)) {
    throw new Error("email already registered");
  }
  if (normalizedUsername && Object.values(store.users).some(({ user }) => user.username === normalizedUsername)) {
    throw new Error("username already taken");
  }

  const userId = createId("user");
  const sessionId = createId("session");
  const user = {
    userId,
    nickname,
    email: normalizedEmail,
    username: normalizedUsername,
    createdAt: new Date().toISOString(),
  };

  store.users[userId] = { user, passwordHash: password };
  store.sessions[sessionId] = userId;
  store.zhihuBindings[userId] = {
    userId,
    zhihuUid: null,
    bindingStatus: "not_started",
    boundAt: null,
    expiredAt: null,
  };
  writeStore(store);
  saveSession(sessionId);

  return {
    user,
    session: { sessionId, userId, createdAt: new Date().toISOString(), expiresAt: "" },
    setupState: "zhihu_pending" as const,
  };
}

function buildMemoryForInterest(interestId: string, level: string, intent: string): MemorySummary {
  const name = interestNames[interestId] || interestId;
  const perspective = intent === "write" ? "写作输出" : intent === "read" ? "高质量输入" : "读写转化";
  return {
    interestId,
    interestName: name,
    knowledgeLevel: level === "advanced" ? "进阶" : level === "beginner" ? "入门" : "中级",
    preferredPerspective: [perspective, "观点形成", "反方质疑"],
    evidencePreference: "案例 + 高质量讨论优先，必要时补充全网资料。",
    writingReminder: `围绕${name}写作时，需要明确立场、补充来源，并让个人经验进入论证。`,
  };
}

function buildProfileFromOnboarding(data: OnboardingPayload, user: AuthResponse["user"]): ProfileData {
  const selected = data.selectedInterests.filter((item) => item.selected);
  const interestMemories = selected.map((item) => buildMemoryForInterest(item.interestId, item.selfRatedLevel, item.intent));
  const interestLabels = interestMemories.map((item) => item.interestName);
  const style = data.writingStyle;

  return {
    nickname: data.nickname || user.nickname,
    accountStatus: "临时画像 · 知乎待关联 · LLM 设置已记录",
    role: "知乎创作者 / 读写一体工作台用户",
    interests: interestLabels,
    avoidances: "不要替我决定立场；不要生成空泛、模板化、没有来源和个人判断的内容。",
    globalMemory: {
      longTermBackground: `${data.nickname || user.nickname} 正在建立创作画像，当前选择了 ${interestLabels.join("、") || "综合创作"} 作为长期兴趣方向。`,
      contentPreference: `偏好从高质量输入中形成观点；证据与判断倾向：${style.evidenceVsJudgment}。`,
      writingStyle: `逻辑深度 ${style.logicDepth}/5，立场鲜明 ${style.stanceSharpness}/5，个人经验意愿 ${style.personalExperienceWillingness}/5，表达锋芒 ${style.expressionSharpness}/5。`,
      recommendationStrategy: "按兴趣小类推荐内容，关注流和偶遇输入作为平级输入来源；每张卡片都要能沉淀观点种子。",
      riskReminder: style.wantsCounterArguments
        ? "写作时必须主动列出反方质疑，避免只输出单边观点。"
        : "写作时保持克制，不强行制造冲突，但仍需说明观点边界。",
    },
    interestMemories,
  };
}

async function mockRequest<T>(path: string, method: string, payload?: unknown): Promise<T> {
  await new Promise((resolve) => window.setTimeout(resolve, 180));
  const [cleanPath, query] = path.split("?");
  const queryParams = new URLSearchParams(query || "");
  const store = readStore();
  const sessionId = getSessionId();
  const userId = sessionId ? store.sessions[sessionId] : null;

  if (method === "POST" && cleanPath === "/api/v1/auth/register") {
    const body = payload as RegisterRequest;
    if (!body.nickname || !body.password) throw new Error("nickname and password are required");
    if (!body.email) throw new Error("email is required");
    return createMockUser(body.nickname, body.password, body.email, body.username) as T;
  }

  if (method === "POST" && cleanPath === "/api/v1/auth/login") {
    const body = payload as LoginRequest;
    for (const { user, passwordHash } of Object.values(store.users)) {
      if (user.email === body.identifier && passwordHash === body.password) {
        const newSessionId = createId("session");
        store.sessions[newSessionId] = user.userId;
        writeStore(store);
        saveSession(newSessionId);
        return {
          user,
          session: { sessionId: newSessionId, userId: user.userId, createdAt: new Date().toISOString(), expiresAt: "" },
          setupState: setupStateForUser(store, user.userId),
        } as T;
      }
    }
    throw new Error("invalid credentials");
  }

  if (method === "GET" && cleanPath === "/api/v1/auth/me") {
    if (!userId || !store.users[userId]) {
      return { authenticated: false, user: null, setupState: null } as T;
    }
    return {
      authenticated: true,
      user: store.users[userId].user,
      setupState: setupStateForUser(store, userId),
    } as T;
  }

  if (method === "POST" && cleanPath === "/api/v1/auth/logout") {
    if (sessionId) delete store.sessions[sessionId];
    writeStore(store);
    clearSession();
    return { success: true } as T;
  }

  if (method === "GET" && cleanPath === "/api/v1/auth/zhihu/authorize") {
    return {
      url: "https://www.zhihu.com/oauth/authorize?client_id=MOCK&redirect_uri=MOCK&response_type=code&scope=MOCK",
    } as T;
  }

  if (method === "GET" && cleanPath === "/api/v1/auth/zhihu/binding") {
    const targetUserId = queryParams.get("user_id") || userId;
    if (!targetUserId) return { bindingStatus: "not_started", userId: "", zhihuUid: null, boundAt: null, expiredAt: null } as T;
    return (store.zhihuBindings[targetUserId] || {
      bindingStatus: "not_started",
      userId: targetUserId,
      zhihuUid: null,
      boundAt: null,
      expiredAt: null,
    }) as T;
  }

  if (method === "DELETE" && cleanPath === "/api/v1/auth/zhihu/binding") {
    const targetUserId = queryParams.get("user_id") || userId;
    if (targetUserId) {
      store.zhihuBindings[targetUserId] = {
        userId: targetUserId,
        zhihuUid: null,
        bindingStatus: "skipped",
        boundAt: null,
        expiredAt: null,
      };
      writeStore(store);
    }
    return { success: true } as T;
  }

  if (method === "POST" && cleanPath === "/api/v1/profile/onboarding") {
    if (!userId || !store.users[userId]) throw new Error("请先登录");
    const body = payload as OnboardingPayload;
    const profile = buildProfileFromOnboarding(body, store.users[userId].user);
    const response: OnboardingResponse = {
      profile,
      profileStatus: "provisional",
      enrichmentJob: { id: createId("enrichment"), status: "queued" },
    };
    store.onboarding[userId] = response;
    writeStore(store);
    return response as T;
  }

  throw new Error(`Mock not implemented: ${method} ${cleanPath}`);
}

async function gatewayRequest<T>(path: string, method: string, payload?: unknown): Promise<T> {
  const url = `${getGatewayBaseUrl()}${path}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const sessionId = getSessionId();
  if (sessionId) headers["x-session-id"] = sessionId;

  const init: RequestInit = { method, headers, cache: "no-store" };
  if (payload !== undefined) init.body = JSON.stringify(payload);

  const response = await fetch(url, init);
  if (!response.ok) {
    // Clear session on 401 (unauthorized)
    if (response.status === 401) {
      clearSession();
    }
    const error = await response.json().catch(() => ({ message: "Request failed" }));
    throw new Error(error.error?.message || error.detail?.message || `HTTP ${response.status}`);
  }

  const body = await response.json();
  if (body.error) throw new Error(body.error.message || "Gateway error");
  return body.data || body;
}

async function request<T>(path: string, method: string, payload?: unknown): Promise<T> {
  return USE_GATEWAY ? gatewayRequest<T>(path, method, payload) : mockRequest<T>(path, method, payload);
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await request<AuthResponse>("/api/v1/auth/register", "POST", data);
  saveSession(response.session.sessionId);
  return response;
}

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await request<AuthResponse>("/api/v1/auth/login", "POST", data);
  saveSession(response.session.sessionId);
  return response;
}

export async function logout(): Promise<{ success: boolean }> {
  return request<{ success: boolean }>("/api/v1/auth/logout", "POST", { sessionId: getSessionId() });
}

export async function getMe(): Promise<AuthMeResponse> {
  try {
    return await request<AuthMeResponse>("/api/v1/auth/me", "GET");
  } catch {
    // Session expired or invalid - return unauthenticated state
    clearSession();
    return { authenticated: false, user: null, setupState: "zhihu_pending" };
  }
}

export async function getZhihuAuthorizeUrl(): Promise<{ url: string }> {
  return request<{ url: string }>("/api/v1/auth/zhihu/authorize", "GET");
}

export async function getZhihuBinding(userId?: string): Promise<ZhihuBindingViewModel> {
  const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request<ZhihuBindingViewModel>(`/api/v1/auth/zhihu/binding${suffix}`, "GET");
}

export async function unbindZhihu(userId?: string): Promise<{ success: boolean }> {
  const suffix = userId ? `?user_id=${encodeURIComponent(userId)}` : "";
  return request<{ success: boolean }>(`/api/v1/auth/zhihu/binding${suffix}`, "DELETE");
}

export async function exchangeZhihuTicket(ticket: string): Promise<ZhihuExchangeTicketResponse> {
  return request<ZhihuExchangeTicketResponse>("/api/v1/auth/zhihu/exchange-ticket", "POST", { ticket });
}

export async function getUserSetupState(): Promise<UserSetupStateData> {
  const me = await getMe();
  const zhihuBinding = me.user ? await getZhihuBinding(me.user.userId) : undefined;
  return {
    authStatus: me.authenticated ? "authenticated" : me.user ? "registered" : "guest",
    setupState: me.setupState || "zhihu_pending",
    zhihuBinding,
  };
}

export async function saveOnboarding(data: OnboardingPayload): Promise<OnboardingResponse> {
  return request<OnboardingResponse>("/api/v1/profile/onboarding", "POST", data);
}

export async function handleZhihuCallback(code: string): Promise<ZhihuBindingViewModel> {
  return request<ZhihuBindingViewModel>(`/api/v1/auth/zhihu/callback?code=${encodeURIComponent(code)}`, "GET");
}

export function setSession(sessionId: string): void {
  saveSession(sessionId);
}

export function getSession(): string | null {
  return getSessionId();
}

export function clearUserSession(): void {
  clearSession();
}
