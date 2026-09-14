# 录播达人 License Server

独立的 NestJS + PostgreSQL 授权服务。它只保存激活码、设备绑定摘要、审计事件和应用版本，不接收平台 Cookie 或录像。

## 安全模型

- 激活码只以带服务端 pepper 的 HMAC-SHA-256 摘要保存；批量创建时明文只返回一次。
- `installation_id` 与设备指纹只保存 SHA-256 摘要。
- 支持月卡（30 天）、季卡（90 天）、年卡（365 天）和终身会员；有效期从激活码首次激活时开始计算。
- 默认每码一台设备；后台可设置会员档位、设备上限、禁用和人工解绑。
- 客户端许可证由 Ed25519 签名，并有有限的离线有效期；联网校验成功会刷新票据。
- 管理后台使用账号密码登录，密码以带随机盐的 scrypt 摘要保存；登录会话只保存在服务端内存中，到期或重启后需要重新登录。
- 私钥、数据库密码、pepper 和初始管理员密码只从环境变量读取，仓库不提供可用默认值。

## 本地启动

需要 Node.js 22+、Docker 和 Docker Compose。

1. 复制 `.env.example` 为 `.env`，将全部 `REPLACE_...` 值替换为独立的随机密钥。
2. 生成 Ed25519 私钥（Node.js 示例）：

   ```sh
   node -e "const{generateKeyPairSync}=require('crypto');const{k}= {k:generateKeyPairSync('ed25519').privateKey};console.log(k.export({type:'pkcs8',format:'pem'}).toString().replace(/\n/g,'\\n'))"
   ```

3. 启动：`docker compose up --build -d`。
4. 设置 `ADMIN_BOOTSTRAP_USERNAME` 和 `ADMIN_BOOTSTRAP_PASSWORD`，首次启动会在账号表为空时创建初始管理员。
5. 通过 HTTPS 反向代理访问 `/admin`，使用管理账号和密码登录。

直接开发时可运行 `npm install`、`npx prisma generate`、`npm run start:dev`。数据库迁移使用 `npx prisma migrate deploy`。

## API

所有 JSON 请求都会拒绝未声明字段。登录成功后，页面使用短期 Bearer 会话访问管理接口。

- `POST /v1/license/activate`：`{ activationCode, installationId, deviceFingerprint }`
- `POST /v1/license/validate`：`{ license: { algorithm, payload, signature }, installationId, deviceFingerprint }`
- `POST /v1/license/deactivate`：请求体同 validate
- `GET /v1/app/version?channel=stable`
- `POST /admin/licenses/batch`：`{ count, plan?, maxDevices?, note? }`；`plan` 可选 `MONTHLY`、`QUARTERLY`、`YEARLY` 或 `LIFETIME`，省略时兼容为终身会员；明文激活码只在该响应出现
- `GET /admin/licenses?search=...`
- `GET /admin/events?licenseId=...`
- `POST /admin/licenses/:id/disable`
- `POST /admin/licenses/:id/unbind`
- `PUT /admin/versions/:channel`：`{ version, downloadUrl?, releaseNotes?, mandatory? }`
- `POST /admin/auth/login`：`{ username, password }`
- `POST /admin/auth/logout`
- `GET /admin/accounts`
- `POST /admin/accounts`：`{ username, password }`
- `PUT /admin/accounts/:id/password`：`{ password }`
- `DELETE /admin/accounts/:id`

客户端应内置并信任服务端 Ed25519 公钥。首次激活响应也包含公钥，便于部署验收，但客户端不能把响应中的任意公钥当作信任根。

## 校验

```sh
npm run typecheck
npm test
npm run build
docker compose config
```
