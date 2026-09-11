import { ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { AdminAuthGuard } from '../src/admin-auth.guard';
import type { AppConfig } from '../src/config';

const config = { adminToken: 'a'.repeat(32) } as AppConfig;
const context = (header?: string) => ({
  switchToHttp: () => ({ getRequest: () => ({ get: () => header }) }),
}) as unknown as ExecutionContext;

describe('AdminAuthGuard', () => {
  const guard = new AdminAuthGuard(config);
  it('accepts the exact bearer token', () => expect(guard.canActivate(context(`Bearer ${config.adminToken}`))).toBe(true));
  it('rejects a missing or incorrect token', () => {
    expect(() => guard.canActivate(context())).toThrow(UnauthorizedException);
    expect(() => guard.canActivate(context('Bearer incorrect'))).toThrow(UnauthorizedException);
  });
});
