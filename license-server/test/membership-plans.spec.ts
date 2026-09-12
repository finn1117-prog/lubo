import { MembershipPlan } from '@prisma/client';
import { membershipExpiry } from '../src/membership-plans';

describe('membership plans', () => {
  const activatedAt = new Date('2026-09-13T00:00:00.000Z');

  it.each([
    [MembershipPlan.MONTHLY, '2026-10-13T00:00:00.000Z'],
    [MembershipPlan.QUARTERLY, '2026-12-12T00:00:00.000Z'],
    [MembershipPlan.YEARLY, '2027-09-13T00:00:00.000Z'],
  ])('calculates %s expiry from first activation', (plan, expected) => {
    expect(membershipExpiry(plan, activatedAt)?.toISOString()).toBe(expected);
  });

  it('keeps lifetime memberships without an expiry', () => {
    expect(membershipExpiry(MembershipPlan.LIFETIME, activatedAt)).toBeNull();
  });
});
