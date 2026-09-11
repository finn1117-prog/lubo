import { BadRequestException, ConflictException, Inject, Injectable, UnauthorizedException } from '@nestjs/common';
import { ActivationEventType, LicenseStatus, Prisma } from '@prisma/client';
import { AppConfig } from './config';
import { keyedHash, LicenseClaims, SignedLicense, signLicense, stableHash, verifyLicense } from './crypto';
import { ActivateDto, LicenseActionDto } from './dto';
import { PrismaService } from './prisma.service';
import type { AuditContext } from './request-context';

@Injectable()
export class LicenseService {
  constructor(private readonly prisma: PrismaService, @Inject('APP_CONFIG') private readonly config: AppConfig) {}

  private identity(input: { installationId: string; deviceFingerprint: string }) {
    return {
      installationHash: stableHash(input.installationId.trim()),
      deviceFingerprintHash: stableHash(input.deviceFingerprint.trim()),
    };
  }

  private issue(licenseId: string, installationHash: string, deviceFingerprintHash: string): SignedLicense {
    const now = new Date();
    const offlineGraceUntil = new Date(now.getTime() + this.config.offlineGraceDays * 86_400_000);
    const claims: LicenseClaims = {
      version: 1,
      licenseId,
      installationHash,
      deviceFingerprintHash,
      status: 'active',
      issuedAt: now.toISOString(),
      expiresAt: null,
      offlineGraceUntil: offlineGraceUntil.toISOString(),
    };
    return signLicense(claims, this.config.privateKeyPem);
  }

  async activate(input: ActivateDto, context: AuditContext) {
    const codeHash = keyedHash(input.activationCode.replace(/[^A-Za-z0-9]/g, '').toUpperCase(), this.config.hashPepper);
    const identity = this.identity(input);

    const result = await this.prisma.$transaction(async (tx) => {
      const license = await tx.licenseCode.findUnique({ where: { codeHash } });
      if (!license || license.status !== LicenseStatus.ACTIVE) throw new UnauthorizedException('Activation code is invalid or disabled');

      const existing = await tx.deviceBinding.findUnique({
        where: { licenseId_installationHash: { licenseId: license.id, installationHash: identity.installationHash } },
      });
      const activeCount = await tx.deviceBinding.count({ where: { licenseId: license.id, active: true } });
      if ((!existing || !existing.active) && activeCount >= license.maxDevices) {
        throw new ConflictException('Activation code has reached its device limit');
      }
      if (existing?.active && existing.deviceFingerprintHash !== identity.deviceFingerprintHash) {
        throw new ConflictException('Installation identity does not match the bound device');
      }

      await tx.deviceBinding.upsert({
        where: { licenseId_installationHash: { licenseId: license.id, installationHash: identity.installationHash } },
        update: { active: true, deviceFingerprintHash: identity.deviceFingerprintHash, lastValidatedAt: new Date(), deactivatedAt: null },
        create: { licenseId: license.id, ...identity },
      });
      await tx.activationEvent.create({ data: { licenseId: license.id, type: ActivationEventType.ACTIVATED, installationHash: identity.installationHash, ...context } });
      return license;
    }, { isolationLevel: Prisma.TransactionIsolationLevel.Serializable });

    return {
      license: this.issue(result.id, identity.installationHash, identity.deviceFingerprintHash),
      publicKey: this.config.publicKeyPem,
      offlineGraceDays: this.config.offlineGraceDays,
      serverTime: new Date().toISOString(),
    };
  }

  async validate(input: LicenseActionDto, context: AuditContext) {
    const claims = this.readAndMatch(input);
    const binding = await this.prisma.deviceBinding.findUnique({
      where: { licenseId_installationHash: { licenseId: claims.licenseId, installationHash: claims.installationHash } },
      include: { license: true },
    });
    if (!binding?.active || binding.license.status !== LicenseStatus.ACTIVE || binding.deviceFingerprintHash !== claims.deviceFingerprintHash) {
      await this.prisma.activationEvent.create({
        data: { licenseId: binding?.licenseId, type: ActivationEventType.VALIDATION_FAILED, installationHash: claims.installationHash, detail: { reason: 'inactive_or_mismatch' }, ...context },
      });
      throw new UnauthorizedException('License is inactive or does not match this device');
    }
    await this.prisma.$transaction([
      this.prisma.deviceBinding.update({ where: { id: binding.id }, data: { lastValidatedAt: new Date() } }),
      this.prisma.activationEvent.create({ data: { licenseId: binding.licenseId, type: ActivationEventType.VALIDATED, installationHash: claims.installationHash, ...context } }),
    ]);
    return { valid: true, license: this.issue(binding.licenseId, claims.installationHash, claims.deviceFingerprintHash), serverTime: new Date().toISOString() };
  }

  async deactivate(input: LicenseActionDto, context: AuditContext) {
    const claims = this.readAndMatch(input);
    const binding = await this.prisma.deviceBinding.findUnique({
      where: { licenseId_installationHash: { licenseId: claims.licenseId, installationHash: claims.installationHash } },
    });
    if (!binding?.active || binding.deviceFingerprintHash !== claims.deviceFingerprintHash) {
      throw new BadRequestException('No active binding exists for this device');
    }
    await this.prisma.$transaction([
      this.prisma.deviceBinding.update({ where: { id: binding.id }, data: { active: false, deactivatedAt: new Date() } }),
      this.prisma.activationEvent.create({ data: { licenseId: binding.licenseId, type: ActivationEventType.DEACTIVATED, installationHash: claims.installationHash, ...context } }),
    ]);
    return { deactivated: true };
  }

  private readAndMatch(input: LicenseActionDto): LicenseClaims {
    let claims: LicenseClaims;
    try { claims = verifyLicense(input.license, this.config.publicKeyPem); }
    catch { throw new UnauthorizedException('License signature is invalid'); }
    const identity = this.identity(input);
    if (claims.installationHash !== identity.installationHash || claims.deviceFingerprintHash !== identity.deviceFingerprintHash) {
      throw new UnauthorizedException('License does not belong to this device');
    }
    return claims;
  }
}
