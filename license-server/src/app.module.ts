import { Module } from '@nestjs/common';
import { AdminAuthGuard } from './admin-auth.guard';
import { AdminAccountsController } from './admin-accounts.controller';
import { AdminAuthController } from './admin-auth.controller';
import { AdminAuthService } from './admin-auth.service';
import { AdminController } from './admin.controller';
import { AdminPageController } from './admin-page.controller';
import { AdminService } from './admin.service';
import { loadConfig } from './config';
import { LicenseController } from './license.controller';
import { LicenseService } from './license.service';
import { PrismaService } from './prisma.service';
import { VersionController } from './version.controller';

@Module({
  controllers: [
    LicenseController,
    VersionController,
    AdminController,
    AdminAuthController,
    AdminAccountsController,
    AdminPageController,
  ],
  providers: [
    PrismaService, LicenseService, AdminService, AdminAuthService, AdminAuthGuard,
    { provide: 'APP_CONFIG', useFactory: loadConfig },
  ],
})
export class AppModule {}
