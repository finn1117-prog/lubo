import { CanActivate, ExecutionContext, Injectable, UnauthorizedException } from '@nestjs/common';
import { AdminAuthService, type AdminRequest } from './admin-auth.service';

@Injectable()
export class AdminAuthGuard implements CanActivate {
  constructor(private readonly auth: AdminAuthService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest<AdminRequest>();
    const token = this.auth.bearerFrom(req);
    if (!token) throw new UnauthorizedException('请先登录管理后台');
    req.adminAccount = await this.auth.authenticate(token);
    return true;
  }
}
