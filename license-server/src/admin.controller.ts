import { Body, Controller, Get, Param, Post, Put, Query, Req, UseGuards } from '@nestjs/common';
import type { Request } from 'express';
import { AdminAuthGuard } from './admin-auth.guard';
import { AdminService } from './admin.service';
import { BatchLicenseDto, SetVersionDto } from './dto';
import { auditContext } from './request-context';

@Controller('admin')
@UseGuards(AdminAuthGuard)
export class AdminController {
  constructor(private readonly admin: AdminService) {}

  @Post('licenses/batch')
  batch(@Body() input: BatchLicenseDto, @Req() req: Request) { return this.admin.createBatch(input, auditContext(req)); }

  @Get('licenses')
  list(@Query('search') search = '') { return this.admin.list(search); }

  @Get('events')
  events(@Query('licenseId') licenseId?: string) { return this.admin.events(licenseId); }

  @Post('licenses/:id/disable')
  disable(@Param('id') id: string, @Req() req: Request) { return this.admin.disable(id, auditContext(req)); }

  @Post('licenses/:id/unbind')
  unbind(@Param('id') id: string, @Req() req: Request) { return this.admin.unbind(id, auditContext(req)); }

  @Put('versions/:channel')
  version(@Param('channel') channel: string, @Body() input: SetVersionDto) { return this.admin.setVersion(channel, input); }
}
