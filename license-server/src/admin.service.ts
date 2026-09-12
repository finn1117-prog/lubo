import { Inject, Injectable, NotFoundException } from '@nestjs/common';
import { ActivationEventType, LicenseStatus, MembershipPlan } from '@prisma/client';
import { AppConfig } from './config';
import { generateActivationCode, keyedHash } from './crypto';
import { BatchLicenseDto, SetVersionDto } from './dto';
import { PrismaService } from './prisma.service';
import type { AuditContext } from './request-context';

@Injectable()
export class AdminService {
  constructor(private readonly prisma: PrismaService, @Inject('APP_CONFIG') private readonly config: AppConfig) {}

  async createBatch(input: BatchLicenseDto, context: AuditContext) {
    const codes = Array.from({ length: input.count }, generateActivationCode);
    const maxDevices = input.maxDevices ?? 1;
    const plan = input.plan ?? MembershipPlan.LIFETIME;
    const created = await this.prisma.$transaction(codes.map((code) => this.prisma.licenseCode.create({
      data: {
        codeHash: keyedHash(code.replace(/-/g, ''), this.config.hashPepper),
        codeHint: code.slice(-5),
        plan,
        maxDevices,
        note: input.note,
        events: { create: { type: ActivationEventType.CREATED, detail: { batchSize: input.count, plan }, ...context } },
      },
      select: { id: true },
    })));
    return { codes: created.map((item, index) => ({ id: item.id, code: codes[index] })) };
  }

  async list(search = '') {
    const value = search.trim().slice(0, 100);
    return this.prisma.licenseCode.findMany({
      where: value ? { OR: [{ id: { contains: value, mode: 'insensitive' } }, { codeHint: { contains: value, mode: 'insensitive' } }, { note: { contains: value, mode: 'insensitive' } }] } : undefined,
      include: { bindings: { orderBy: { activatedAt: 'desc' } }, _count: { select: { events: true } } },
      orderBy: { createdAt: 'desc' },
      take: 200,
    });
  }

  async events(licenseId?: string) {
    return this.prisma.activationEvent.findMany({
      where: licenseId ? { licenseId } : undefined,
      orderBy: { createdAt: 'desc' },
      take: 200,
    });
  }

  async disable(id: string, context: AuditContext) {
    await this.ensureLicense(id);
    await this.prisma.$transaction([
      this.prisma.licenseCode.update({ where: { id }, data: { status: LicenseStatus.DISABLED } }),
      this.prisma.deviceBinding.updateMany({ where: { licenseId: id, active: true }, data: { active: false, deactivatedAt: new Date() } }),
      this.prisma.activationEvent.create({ data: { licenseId: id, type: ActivationEventType.DISABLED, ...context } }),
    ]);
    return { disabled: true };
  }

  async unbind(id: string, context: AuditContext) {
    await this.ensureLicense(id);
    const [, event] = await this.prisma.$transaction([
      this.prisma.deviceBinding.updateMany({ where: { licenseId: id, active: true }, data: { active: false, deactivatedAt: new Date() } }),
      this.prisma.activationEvent.create({ data: { licenseId: id, type: ActivationEventType.UNBOUND, ...context } }),
    ]);
    return { unbound: true, eventId: event.id };
  }

  setVersion(channel: string, input: SetVersionDto) {
    const safeChannel = channel.trim().slice(0, 40);
    return this.prisma.appVersion.upsert({
      where: { channel: safeChannel },
      update: input,
      create: { channel: safeChannel, ...input },
    });
  }

  private async ensureLicense(id: string) {
    if (!await this.prisma.licenseCode.findUnique({ where: { id }, select: { id: true } })) throw new NotFoundException('License not found');
  }
}
