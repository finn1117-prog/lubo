import { Controller, Get, NotFoundException, Query } from '@nestjs/common';
import { PrismaService } from './prisma.service';

@Controller('v1/app')
export class VersionController {
  constructor(private readonly prisma: PrismaService) {}

  @Get('version')
  async get(@Query('channel') channel = 'stable') {
    const version = await this.prisma.appVersion.findUnique({ where: { channel: channel.slice(0, 40) } });
    if (!version) throw new NotFoundException('No version is configured for this channel');
    return version;
  }
}
