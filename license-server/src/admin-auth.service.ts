import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Inject,
  Injectable,
  NotFoundException,
  OnApplicationBootstrap,
  UnauthorizedException,
} from '@nestjs/common';
import { createHash, randomBytes, scrypt as scryptCallback, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import type { AppConfig } from './config';
import { PrismaService } from './prisma.service';

const scrypt = promisify(scryptCallback);

export interface AdminIdentity {
  id: string;
  username: string;
}

interface SessionRecord extends AdminIdentity {
  expiresAt: number;
}

export interface AdminRequest {
  get(name: string): string | undefined;
  adminAccount?: AdminIdentity;
}

@Injectable()
export class AdminAuthService implements OnApplicationBootstrap {
  private readonly sessions = new Map<string, SessionRecord>();

  constructor(
    private readonly prisma: PrismaService,
    @Inject('APP_CONFIG') private readonly config: AppConfig,
  ) {}

  async onApplicationBootstrap(): Promise<void> {
    if (await this.prisma.adminAccount.count() > 0) return;
    await this.prisma.adminAccount.create({
      data: {
        username: this.config.adminBootstrapUsername,
        passwordHash: await this.hashPassword(this.config.adminBootstrapPassword),
      },
    });
  }

  async login(username: string, password: string) {
    const account = await this.prisma.adminAccount.findUnique({ where: { username } });
    if (!account?.active || !(await this.verifyPassword(password, account.passwordHash))) {
      throw new UnauthorizedException('账号或密码错误');
    }
    const token = randomBytes(32).toString('base64url');
    const expiresAt = Date.now() + this.config.adminSessionHours * 60 * 60 * 1000;
    this.sessions.set(this.tokenHash(token), { id: account.id, username: account.username, expiresAt });
    await this.prisma.adminAccount.update({ where: { id: account.id }, data: { lastLoginAt: new Date() } });
    return { token, expiresAt: new Date(expiresAt).toISOString(), account: this.publicAccount(account) };
  }

  logout(token: string): void {
    if (token) this.sessions.delete(this.tokenHash(token));
  }

  async authenticate(token: string): Promise<AdminIdentity> {
    const key = this.tokenHash(token);
    const session = this.sessions.get(key);
    if (!session || session.expiresAt <= Date.now()) {
      this.sessions.delete(key);
      throw new UnauthorizedException('登录已失效，请重新登录');
    }
    const account = await this.prisma.adminAccount.findUnique({ where: { id: session.id } });
    if (!account?.active) {
      this.sessions.delete(key);
      throw new UnauthorizedException('账号已停用或删除');
    }
    return { id: account.id, username: account.username };
  }

  async listAccounts() {
    const accounts = await this.prisma.adminAccount.findMany({ orderBy: { createdAt: 'asc' } });
    return accounts.map((account) => this.publicAccount(account));
  }

  async createAccount(username: string, password: string) {
    const exists = await this.prisma.adminAccount.findUnique({ where: { username } });
    if (exists) throw new ConflictException('账号已存在');
    const account = await this.prisma.adminAccount.create({
      data: { username, passwordHash: await this.hashPassword(password) },
    });
    return this.publicAccount(account);
  }

  async changePassword(id: string, password: string) {
    const account = await this.prisma.adminAccount.findUnique({ where: { id } });
    if (!account) throw new NotFoundException('账号不存在');
    await this.prisma.adminAccount.update({
      where: { id },
      data: { passwordHash: await this.hashPassword(password) },
    });
    this.revokeAccountSessions(id);
    return { changed: true };
  }

  async deleteAccount(id: string, currentAccountId: string) {
    if (id === currentAccountId) throw new ForbiddenException('不能删除当前登录账号');
    const account = await this.prisma.adminAccount.findUnique({ where: { id } });
    if (!account) throw new NotFoundException('账号不存在');
    if (await this.prisma.adminAccount.count({ where: { active: true } }) <= 1) {
      throw new BadRequestException('至少需要保留一个管理账号');
    }
    await this.prisma.adminAccount.delete({ where: { id } });
    this.revokeAccountSessions(id);
    return { deleted: true };
  }

  bearerFrom(request: AdminRequest): string {
    const authorization = request.get('authorization') ?? '';
    return authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  }

  private async hashPassword(password: string): Promise<string> {
    const salt = randomBytes(16);
    const derived = (await scrypt(password, salt, 64)) as Buffer;
    return `scrypt$${salt.toString('hex')}$${derived.toString('hex')}`;
  }

  private async verifyPassword(password: string, stored: string): Promise<boolean> {
    const [algorithm, saltHex, hashHex] = stored.split('$');
    if (algorithm !== 'scrypt' || !saltHex || !hashHex) return false;
    const expected = Buffer.from(hashHex, 'hex');
    const actual = (await scrypt(password, Buffer.from(saltHex, 'hex'), expected.length)) as Buffer;
    return actual.length === expected.length && timingSafeEqual(actual, expected);
  }

  private tokenHash(token: string): string {
    return createHash('sha256').update(token).digest('hex');
  }

  private revokeAccountSessions(accountId: string): void {
    for (const [token, session] of this.sessions) {
      if (session.id === accountId) this.sessions.delete(token);
    }
  }

  private publicAccount(account: {
    id: string;
    username: string;
    active: boolean;
    lastLoginAt: Date | null;
    createdAt: Date;
    updatedAt: Date;
  }) {
    return {
      id: account.id,
      username: account.username,
      active: account.active,
      lastLoginAt: account.lastLoginAt,
      createdAt: account.createdAt,
      updatedAt: account.updatedAt,
    };
  }
}
