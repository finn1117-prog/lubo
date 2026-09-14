import { Body, Controller, Delete, Get, Param, Post, Put, Req, UseGuards } from '@nestjs/common';
import { AdminAuthGuard } from './admin-auth.guard';
import { AdminAuthService, type AdminRequest } from './admin-auth.service';
import { ChangeAdminPasswordDto, CreateAdminAccountDto } from './dto';

@Controller('admin/accounts')
@UseGuards(AdminAuthGuard)
export class AdminAccountsController {
  constructor(private readonly auth: AdminAuthService) {}

  @Get()
  list() {
    return this.auth.listAccounts();
  }

  @Post()
  create(@Body() input: CreateAdminAccountDto) {
    return this.auth.createAccount(input.username, input.password);
  }

  @Put(':id/password')
  changePassword(@Param('id') id: string, @Body() input: ChangeAdminPasswordDto) {
    return this.auth.changePassword(id, input.password);
  }

  @Delete(':id')
  delete(@Param('id') id: string, @Req() request: AdminRequest) {
    return this.auth.deleteAccount(id, request.adminAccount!.id);
  }
}
