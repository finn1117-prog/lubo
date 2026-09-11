# 录播达人 License Server

独立的 NestJS + PostgreSQL 授权服务。它只保存激活码、设备绑定摘要、审计事件和应用版本，不接收平台 Cookie 或录像。

## 安全模型

- 激活码只以带服务端 pepper 的 HMAC-SHA-256 摘要保存；批量创建时明文只返回一次。
- `installation_id` 与设备指纹只保存 SHA-256 摘要。
- 默认每码一台设备；后台可设置上限、禁用和人工解绑。
- 客户端许可证由 Ed25519 签名，并有有限的离线有效期；联网校验成功会刷新票据。
- 管理 API 使用恒定时间比较的 Bearer token。生产环境应由 Caddy、Nginx 或云负载均衡器终止 HTTPS，且不要直接暴露容器端口。
- 私钥、数据库密码、pepper 和管理令牌只从环境变量读取，仓库不提供可用默认值。

## 本地启动

需要 Node.js 22+、Docker 和 Docker Compose。

1. 复制 `.env.example` 为 `.env`，将全部 `REPLACE_...` 值替换为独立的随机密钥。
2. 生成 Ed25519 私钥（Node.js 示例）：

   ```sh
   node -e "const{generateKeyPairSync}=require('crypto');const{k}= {k:generateKeyPairSync('ed25519').privateKey};console.log(k.export({type:'pkcs8',format:'pem'}).toString().replace(/\n/g,'\\n'))"
   ```

3. 启动：`docker compose up --build -d`。
4. 通过 HTTPS 反向代理访问 `/admin`。页面会要求输入 `ADMIN_TOKEN`，令牌只保存在当前页面内存中。

直接开发时可运行 `npm install`、`npx prisma generate`、`npm run start:dev`。数据库迁移使用 `npx prisma migrate deploy`。

## API

所有 JSON 请求都会拒绝未声明字段。管理接口需要 `Authorization: Bearer <ADMIN_TOKEN>`。

- `POST /v1/license/activate`：`{ activationCode, installationId, deviceFingerprint }`
- `POST /v1/license/validate`：`{ license: { algorithm, payload, signature }, installationId, deviceFingerprint }`
- `POST /v1/license/deactivate`：请求体同 validate
- `GET /v1/app/version?channel=stable`
- `POST /admin/licenses/batch`：`{ count, maxDevices?, note? }`；明文激活码只在该响应出现
- `GET /admin/licenses?search=...`
- `GET /admin/events?licenseId=...`
- `POST /admin/licenses/:id/disable`
- `POST /admin/licenses/:id/unbind`
- `PUT /admin/versions/:channel`：`{ version, downloadUrl?, releaseNotes?, mandatory? }`

客户端应内置并信任服务端 Ed25519 公钥。首次激活响应也包含公钥，便于部署验收，但客户端不能把响应中的任意公钥当作信任根。

## 校验

```sh
npm run typecheck
npm test
npm run build
docker compose config
```
