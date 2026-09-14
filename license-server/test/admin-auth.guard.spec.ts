import { ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { AdminAuthGuard } from '../src/admin-auth.guard';
import type { AdminAuthService } from '../src/admin-auth.service';

const request = (header?: string) => ({ get: () => header, adminAccount: undefined });
const context = (req: ReturnType<typeof request>) => ({
  switchToHttp: () => ({ getRequest: () => req }),
}) as unknown as ExecutionContext;

describe('AdminAuthGuard', () => {
  const auth = {
    bearerFrom: (req: ReturnType<typeof request>) => (req.get()?.startsWith('Bearer ') ? req.get()!.slice(7) : ''),
    authenticate: jest.fn(async (token: string) => {
      if (token !== 'valid-session') throw new UnauthorizedException();
      return { id: 'admin-1', username: 'admin' };
    }),
  } as unknown as AdminAuthService;
  const guard = new AdminAuthGuard(auth);

  it('accepts a valid session and attaches the account', async () => {
    const req = request('Bearer valid-session');
    await expect(guard.canActivate(context(req))).resolves.toBe(true);
    expect(req.adminAccount).toEqual({ id: 'admin-1', username: 'admin' });
  });

  it('rejects a missing or invalid session', async () => {
    await expect(guard.canActivate(context(request()))).rejects.toThrow(UnauthorizedException);
    await expect(guard.canActivate(context(request('Bearer incorrect')))).rejects.toThrow(UnauthorizedException);
  });
});
