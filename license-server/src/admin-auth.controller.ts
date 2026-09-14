import { Body, Controller, Get, Post, Req, UseGuards } from '@nestjs/common';
import { AdminAuthGuard } from './admin-auth.guard';
import { AdminAuthService, type AdminRequest } from './admin-auth.service';
import { AdminLoginDto } from './dto';

@Controller('admin/auth')
export class AdminAuthController {
  constructor(private readonly auth: AdminAuthService) {}

  @Post('login')
  login(@Body() input: AdminLoginDto) {
    return this.auth.login(input.username, input.password);
  }

  @Get('me')
  @UseGuards(AdminAuthGuard)
  me(@Req() request: AdminRequest) {
    return request.adminAccount;
  }

  @Post('logout')
  @UseGuards(AdminAuthGuard)
  logout(@Req() request: AdminRequest) {
    this.auth.logout(this.auth.bearerFrom(request));
    return { loggedOut: true };
  }
}
