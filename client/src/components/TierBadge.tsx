import type { Tier } from "../types";

const TIER_LABELS: Record<Tier, string> = {
  green: "Green",
  watch: "Watch",
  caution: "Caution",
  emergency: "Emergency",
};

export default function TierBadge({ tier }: { tier: Tier | null }) {
  if (!tier) return <span className="tier-badge tier-pending">Pending</span>;
  return <span className={`tier-badge tier-${tier}`}>{TIER_LABELS[tier]}</span>;
}
