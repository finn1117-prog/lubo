import { generateKeyPairSync } from 'node:crypto';
import { canonicalJson, generateActivationCode, keyedHash, normalizeCode, signLicense, verifyLicense } from '../src/crypto';

describe('license cryptography', () => {
  const keys = generateKeyPairSync('ed25519');
  const privateKey = keys.privateKey.export({ type: 'pkcs8', format: 'pem' }).toString();
  const publicKey = keys.publicKey.export({ type: 'spki', format: 'pem' }).toString();
  const claims = { version: 1 as const, licenseId: 'license-1', installationHash: 'a'.repeat(64), deviceFingerprintHash: 'b'.repeat(64), status: 'active' as const, issuedAt: new Date().toISOString(), expiresAt: null, offlineGraceUntil: new Date(Date.now() + 1000).toISOString() };

  it('round-trips an Ed25519 signed license', () => {
    expect(verifyLicense(signLicense(claims, privateKey), publicKey)).toEqual(claims);
  });

  it('rejects a modified payload', () => {
    const document = signLicense(claims, privateKey);
    document.payload = Buffer.from(JSON.stringify({ ...claims, licenseId: 'changed' })).toString('base64url');
    expect(() => verifyLicense(document, publicKey)).toThrow('Invalid');
  });

  it('normalizes code formatting and hashes without retaining plaintext', () => {
    expect(normalizeCode('sc-ab12-cd34')).toBe('SCAB12CD34');
    expect(keyedHash('SCAB12CD34', 'x'.repeat(32))).toMatch(/^[a-f0-9]{64}$/);
    expect(generateActivationCode()).toMatch(/^SC-(?:[A-F0-9]{5}-){5}[A-F0-9]{5}$/);
  });

  it('matches the deterministic cross-language canonical JSON fixture', () => {
    const fixtureKey = `-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEIJ1hsZ3v/VpguoRK9JLsLMREScVpezJpGXA7rAMcrn9g\n-----END PRIVATE KEY-----\n`;
    const fixtureClaims = {
      version: 1 as const,
      status: 'active' as const,
      licenseId: 'fixture-license',
      installationHash: 'aaaa',
      deviceFingerprintHash: 'bbbb',
      issuedAt: '2026-09-11T00:00:00.000Z',
      expiresAt: null,
      offlineGraceUntil: '2026-09-18T00:00:00.000Z',
    };
    expect(canonicalJson({ z: 1, a: { y: 2, x: 3 } })).toBe('{"a":{"x":3,"y":2},"z":1}');
    expect(signLicense(fixtureClaims, fixtureKey)).toEqual({
      algorithm: 'Ed25519',
      payload: 'eyJkZXZpY2VGaW5nZXJwcmludEhhc2giOiJiYmJiIiwiZXhwaXJlc0F0IjpudWxsLCJpbnN0YWxsYXRpb25IYXNoIjoiYWFhYSIsImlzc3VlZEF0IjoiMjAyNi0wOS0xMVQwMDowMDowMC4wMDBaIiwibGljZW5zZUlkIjoiZml4dHVyZS1saWNlbnNlIiwib2ZmbGluZUdyYWNlVW50aWwiOiIyMDI2LTA5LTE4VDAwOjAwOjAwLjAwMFoiLCJzdGF0dXMiOiJhY3RpdmUiLCJ2ZXJzaW9uIjoxfQ',
      signature: 'UGrDpzAyiWPn06j1DTKIvFEKm6_dvIHi41GCGYEWOs85Yi-QpFsZucZ-zeo8DQoFVmQ143XsnGbLOUqClpaKDw',
    });
  });
});
