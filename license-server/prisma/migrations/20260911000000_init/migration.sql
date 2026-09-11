CREATE TYPE "LicenseStatus" AS ENUM ('ACTIVE', 'DISABLED');
CREATE TYPE "ActivationEventType" AS ENUM ('CREATED', 'ACTIVATED', 'VALIDATED', 'DEACTIVATED', 'DISABLED', 'UNBOUND', 'VALIDATION_FAILED');

CREATE TABLE "license_codes" (
  "id" TEXT NOT NULL,
  "code_hash" TEXT NOT NULL,
  "code_hint" TEXT NOT NULL,
  "status" "LicenseStatus" NOT NULL DEFAULT 'ACTIVE',
  "max_devices" INTEGER NOT NULL DEFAULT 1,
  "note" TEXT,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "license_codes_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "license_codes_code_hash_key" ON "license_codes"("code_hash");

CREATE TABLE "device_bindings" (
  "id" TEXT NOT NULL,
  "license_id" TEXT NOT NULL,
  "installation_hash" TEXT NOT NULL,
  "device_fingerprint_hash" TEXT NOT NULL,
  "active" BOOLEAN NOT NULL DEFAULT true,
  "activated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "last_validated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "deactivated_at" TIMESTAMP(3),
  CONSTRAINT "device_bindings_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX "device_bindings_license_id_installation_hash_key" ON "device_bindings"("license_id", "installation_hash");
CREATE INDEX "device_bindings_license_id_active_idx" ON "device_bindings"("license_id", "active");
ALTER TABLE "device_bindings" ADD CONSTRAINT "device_bindings_license_id_fkey" FOREIGN KEY ("license_id") REFERENCES "license_codes"("id") ON DELETE CASCADE ON UPDATE CASCADE;

CREATE TABLE "activation_events" (
  "id" TEXT NOT NULL,
  "license_id" TEXT,
  "type" "ActivationEventType" NOT NULL,
  "installation_hash" TEXT,
  "ip_address" TEXT,
  "user_agent" TEXT,
  "detail" JSONB,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "activation_events_pkey" PRIMARY KEY ("id")
);
CREATE INDEX "activation_events_license_id_created_at_idx" ON "activation_events"("license_id", "created_at");
ALTER TABLE "activation_events" ADD CONSTRAINT "activation_events_license_id_fkey" FOREIGN KEY ("license_id") REFERENCES "license_codes"("id") ON DELETE SET NULL ON UPDATE CASCADE;

CREATE TABLE "app_versions" (
  "channel" TEXT NOT NULL DEFAULT 'stable',
  "version" TEXT NOT NULL,
  "download_url" TEXT,
  "release_notes" TEXT,
  "mandatory" BOOLEAN NOT NULL DEFAULT false,
  "updated_at" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "app_versions_pkey" PRIMARY KEY ("channel")
);
