import { Type } from 'class-transformer';
import { MembershipPlan } from '@prisma/client';
import { IsBoolean, IsEnum, IsInt, IsNotEmpty, IsOptional, IsString, IsUrl, Length, Matches, Max, MaxLength, Min, ValidateNested } from 'class-validator';
import type { SignedLicense } from './crypto';

export class DeviceDto {
  @IsString() @Length(8, 200) installationId!: string;
  @IsString() @Length(16, 500) deviceFingerprint!: string;
}

export class ActivateDto extends DeviceDto {
  @IsString() @Length(8, 128) activationCode!: string;
}

export class SignedLicenseDto implements SignedLicense {
  @IsString() algorithm!: 'Ed25519';
  @IsString() @IsNotEmpty() payload!: string;
  @IsString() @IsNotEmpty() signature!: string;
}

export class LicenseActionDto extends DeviceDto {
  @ValidateNested() @Type(() => SignedLicenseDto) license!: SignedLicenseDto;
}

export class BatchLicenseDto {
  @IsInt() @Min(1) @Max(1000) count!: number;
  @IsOptional() @IsEnum(MembershipPlan) plan?: MembershipPlan;
  @IsOptional() @IsInt() @Min(1) @Max(10) maxDevices?: number;
  @IsOptional() @IsString() @MaxLength(500) note?: string;
}

export class SetVersionDto {
  @IsString() @Length(1, 50) version!: string;
  @IsOptional() @IsUrl({ require_protocol: true }) downloadUrl?: string;
  @IsOptional() @IsString() @MaxLength(5000) releaseNotes?: string;
  @IsOptional() @IsBoolean() mandatory?: boolean;
}

export class AdminLoginDto {
  @IsString() @Matches(/^[A-Za-z0-9_.-]{3,32}$/) username!: string;
  @IsString() @Length(8, 128) password!: string;
}

export class CreateAdminAccountDto {
  @IsString() @Matches(/^[A-Za-z0-9_.-]{3,32}$/) username!: string;
  @IsString() @Length(10, 128) password!: string;
}

export class ChangeAdminPasswordDto {
  @IsString() @Length(10, 128) password!: string;
}
