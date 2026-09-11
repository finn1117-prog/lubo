import { createPrivateKey, createPublicKey } from 'node:crypto';

export interface AppConfig {
  adminToken: string;
  hashPepper: string;
  privateKeyPem: string;
  publicKeyPem: string;
  offlineGraceDays: number;
  port: number;
}

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is required`);
  return value.replace(/\\n/g, '\n');
}

export function loadConfig(): AppConfig {
  const adminToken = required('ADMIN_TOKEN');
  const hashPepper = required('LICENSE_HASH_PEPPER');
  const privateKeyPem = required('LICENSE_ED25519_PRIVATE_KEY');
  if (adminToken.length < 32) throw new Error('ADMIN_TOKEN must be at least 32 characters');
  if (hashPepper.length < 32) throw new Error('LICENSE_HASH_PEPPER must be at least 32 characters');

  const privateKey = createPrivateKey(privateKeyPem);
  if (privateKey.asymmetricKeyType !== 'ed25519') {
    throw new Error('LICENSE_ED25519_PRIVATE_KEY must be an Ed25519 private key');
  }
  const publicKeyPem = createPublicKey(privateKey).export({ type: 'spki', format: 'pem' }).toString();
  const offlineGraceDays = Number.parseInt(process.env.OFFLINE_GRACE_DAYS ?? '7', 10);
  if (!Number.isInteger(offlineGraceDays) || offlineGraceDays < 0 || offlineGraceDays > 30) {
    throw new Error('OFFLINE_GRACE_DAYS must be between 0 and 30');
  }
  const port = Number.parseInt(process.env.PORT ?? '3000', 10);
  return { adminToken, hashPepper, privateKeyPem, publicKeyPem, offlineGraceDays, port };
}
