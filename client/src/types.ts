export type Tier = "green" | "watch" | "caution" | "emergency";

export type IllustrationVariant = "calm" | "rocky" | "wooded" | "bridge" | "wetland";

export interface Classification {
  tier: Tier | null;
  confidence: number | null;
  reasoning: string | null;
}

export type Condition = "clear" | "murky" | "flooded" | "whitewater" | "algae" | "debris";

export interface ConditionScore {
  label: Condition;
  similarity: number;
}

export interface ConditionResult {
  label: Condition;
  similarity: number;
  scores: ConditionScore[];
}

export interface VisualMatch {
  segmentCode: string;
  similarity: number;
}

export type ReportStatus = "queued" | "processing" | "classified" | "failed";

export interface ReportItem {
  id: string;
  reporter: string;
  segmentCode: string;
  description: string;
  imagePath: string | null;
  status: ReportStatus;
  classification: Classification;
  visualMatches: VisualMatch[];
  condition: ConditionResult | null;
  userTag?: Condition | null;
  createdAt: string;
}

export interface WorldLocation {
  code: string;
  name: string;
  description: string;
  illustration: IllustrationVariant;
  lat: number;
  lng: number;
  reportCount: number;
  imageCount: number;
  currentTier: Tier | null;
  lastReportAt: string | null;
  latestImagePath?: string | null;
}

export interface UserPublic {
  id: string;
  username: string;
}

export interface AuthResponse {
  token: string;
  user: UserPublic;
}

export interface AlertSettings {
  channels: string[];
  radiusMeters: number;
  minTier: Tier;
  homeSegmentCode: string | null;
}

export interface UserMe {
  id: string;
  username: string;
  alertSettings: AlertSettings;
}

export interface AlertRecord {
  id: string;
  tier: string;
  segmentCode: string;
  message: string;
  sentAt: string;
}

export interface MlStatus {
  torchInstalled: boolean;
  trained: boolean;
  classes: Condition[];
  instructions: string;
}
