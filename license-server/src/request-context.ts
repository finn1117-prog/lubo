import type { Request } from 'express';

export interface AuditContext { ipAddress?: string; userAgent?: string; }

export function auditContext(req: Request): AuditContext {
  return { ipAddress: req.ip?.slice(0, 100), userAgent: req.get('user-agent')?.slice(0, 500) };
}
