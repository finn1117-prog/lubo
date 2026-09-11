import { createHash, createHmac, randomBytes, sign, verify } from 'node:crypto';

export interface LicenseClaims {
  version: 1;
  licenseId: string;
  installationHash: string;
  deviceFingerprintHash: string;
  status: 'active';
  issuedAt: string;
  expiresAt: null;
  offlineGraceUntil: string;
}

export interface SignedLicense {
  algorithm: 'Ed25519';
  payload: string;
  signature: string;
}

export const normalizeCode = (value: string): string => value.replace(/[^A-Za-z0-9]/g, '').toUpperCase();

export function keyedHash(value: string, pepper: string): string {
  return createHmac('sha256', pepper).update(value, 'utf8').digest('hex');
}

export function stableHash(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

export function generateActivationCode(): string {
  const value = randomBytes(15).toString('hex').toUpperCase();
  return `SC-${value.match(/.{1,5}/g)!.join('-')}`;
}

export function signLicense(claims: LicenseClaims, privateKeyPem: string): SignedLicense {
  const payloadBytes = Buffer.from(canonicalJson(claims), 'utf8');
  const payload = payloadBytes.toString('base64url');
  const signature = sign(null, payloadBytes, privateKeyPem).toString('base64url');
  return { algorithm: 'Ed25519', payload, signature };
}

export function verifyLicense(document: SignedLicense, publicKeyPem: string): LicenseClaims {
  const payloadBytes = Buffer.from(document.payload, 'base64url');
  if (document.algorithm !== 'Ed25519' || !verify(null, payloadBytes, publicKeyPem, Buffer.from(document.signature, 'base64url'))) {
    throw new Error('Invalid license signature');
  }
  const claims = JSON.parse(payloadBytes.toString('utf8')) as LicenseClaims;
  if (claims.version !== 1 || !claims.licenseId || !claims.installationHash || !claims.deviceFingerprintHash) {
    throw new Error('Invalid license claims');
  }
  return claims;
}

export function canonicalJson(value: unknown): string {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(',')}}`;
}
