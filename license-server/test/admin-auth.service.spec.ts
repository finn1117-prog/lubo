import { ForbiddenException, UnauthorizedException } from '@nestjs/common';
import { AdminAuthService } from '../src/admin-auth.service';
import type { AppConfig } from '../src/config';

describe('AdminAuthService', () => {
  const config = {
    adminBootstrapUsername: 'admin',
    adminBootstrapPassword: 'initial-password-123',
    adminSessionHours: 12,
  } as AppConfig;

  function fixture() {
    const accounts: any[] = [];
    const prisma = {
      adminAccount: {
        count: jest.fn(async () => accounts.filter((x) => x.active).length),
        create: jest.fn(async ({ data }) => {
          const account = {
            id: `account-${accounts.length + 1}`,
            active: true,
            lastLoginAt: null,
            createdAt: new Date(),
            updatedAt: new Date(),
            ...data,
          };
          accounts.push(account);
          return account;
        }),
        findUnique: jest.fn(async ({ where }) => accounts.find((x) => x.id === where.id || x.username === where.username) ?? null),
        findMany: jest.fn(async () => accounts),
        update: jest.fn(async ({ where, data }) => {
          const account = accounts.find((x) => x.id === where.id);
          Object.assign(account, data, { updatedAt: new Date() });
          return account;
        }),
        delete: jest.fn(async ({ where }) => {
          const index = accounts.findIndex((x) => x.id === where.id);
          return accounts.splice(index, 1)[0];
        }),
      },
    };
    return { service: new AdminAuthService(prisma as never, config), accounts };
  }

  it('creates the first account and authenticates it with a temporary session', async () => {
    const { service } = fixture();
    await service.onApplicationBootstrap();
    const login = await service.login('admin', 'initial-password-123');
    expect(login.token).toHaveLength(43);
    await expect(service.authenticate(login.token)).resolves.toEqual({ id: 'account-1', username: 'admin' });
    await expect(service.login('admin', 'wrong-password')).rejects.toThrow(UnauthorizedException);
  });

  it('prevents deleting the currently signed-in account', async () => {
    const { service } = fixture();
    await service.onApplicationBootstrap();
    await expect(service.deleteAccount('account-1', 'account-1')).rejects.toThrow(ForbiddenException);
  });
});
