import { Body, Controller, Post, Req } from '@nestjs/common';
import type { Request } from 'express';
import { ActivateDto, LicenseActionDto } from './dto';
import { LicenseService } from './license.service';
import { auditContext } from './request-context';

@Controller('v1/license')
export class LicenseController {
  constructor(private readonly licenses: LicenseService) {}

  @Post('activate')
  activate(@Body() input: ActivateDto, @Req() req: Request) { return this.licenses.activate(input, auditContext(req)); }

  @Post('validate')
  validate(@Body() input: LicenseActionDto, @Req() req: Request) { return this.licenses.validate(input, auditContext(req)); }

  @Post('deactivate')
  deactivate(@Body() input: LicenseActionDto, @Req() req: Request) { return this.licenses.deactivate(input, auditContext(req)); }
}
