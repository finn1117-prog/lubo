import { CanActivate, ExecutionContext, Inject, Injectable, UnauthorizedException } from '@nestjs/common';
import { timingSafeEqual } from 'node:crypto';
import type { Request } from 'express';
import type { AppConfig } from './config';

@Injectable()
export class AdminAuthGuard implements CanActivate {
  constructor(@Inject('APP_CONFIG') private readonly config: AppConfig) {}

  canActivate(context: ExecutionContext): boolean {
    const req = context.switchToHttp().getRequest<Request>();
    const authorization = req.get('authorization') ?? '';
    const supplied = authorization.startsWith('Bearer ') ? authorization.slice(7) : '';
    const actual = Buffer.from(supplied);
    const expected = Buffer.from(this.config.adminToken);
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
      throw new UnauthorizedException('Valid admin bearer token required');
    }
    return true;
  }
}
