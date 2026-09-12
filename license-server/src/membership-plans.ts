import { MembershipPlan } from '@prisma/client';

export const MEMBERSHIP_PLAN_DAYS: Record<MembershipPlan, number | null> = {
  MONTHLY: 30,
  QUARTERLY: 90,
  YEARLY: 365,
  LIFETIME: null,
};

export function membershipExpiry(plan: MembershipPlan, activatedAt: Date): Date | null {
  const days = MEMBERSHIP_PLAN_DAYS[plan];
  return days === null ? null : new Date(activatedAt.getTime() + days * 86_400_000);
}

