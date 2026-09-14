import { createPrivateKey, createPublicKey } from 'node:crypto';

export interface AppConfig {
  adminBootstrapUsername: string;
  adminBootstrapPassword: string;
  adminSessionHours: number;
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
  const adminBootstrapUsername = (process.env.ADMIN_BOOTSTRAP_USERNAME ?? 'admin').trim();
  const adminBootstrapPassword = required('ADMIN_BOOTSTRAP_PASSWORD');
  const adminSessionHours = Number.parseInt(process.env.ADMIN_SESSION_HOURS ?? '12', 10);
  const hashPepper = required('LICENSE_HASH_PEPPER');
  const privateKeyPem = required('LICENSE_ED25519_PRIVATE_KEY');
  if (!/^[A-Za-z0-9_.-]{3,32}$/.test(adminBootstrapUsername)) {
    throw new Error('ADMIN_BOOTSTRAP_USERNAME must be 3-32 letters, numbers, dots, dashes or underscores');
  }
  if (adminBootstrapPassword.length < 12) {
    throw new Error('ADMIN_BOOTSTRAP_PASSWORD must be at least 12 characters');
  }
  if (!Number.isInteger(adminSessionHours) || adminSessionHours < 1 || adminSessionHours > 72) {
    throw new Error('ADMIN_SESSION_HOURS must be between 1 and 72');
  }
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
  return {
    adminBootstrapUsername,
    adminBootstrapPassword,
    adminSessionHours,
    hashPepper,
    privateKeyPem,
    publicKeyPem,
    offlineGraceDays,
    port,
  };
}
