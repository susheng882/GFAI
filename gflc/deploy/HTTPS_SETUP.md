# GFLC HTTPS（TLS）部署：四步命令

> 适用文件：`nginx-ssl.conf.example`、`docker-compose.ssl.yml`、`certs/`（证书目录）。
> **硬门禁：未拿到可信 CA 签发的证书之前，G3 不算完成，禁止对外宣称全站 HTTPS。**
> 自签证书仅可用于内网验证，不能替代 G3。ICP 备案是另一项独立外部待办（G7），不可由本配置代替。

---

## 第一步：申请证书（外部动作，需域名与公网 IP）

选择以下任一方式，目标是拿到两个文件：`fullchain.pem`（证书链）与 `privkey.pem`（私钥）。

```bash
# 方式 A：云厂商免费证书（阿里云/腾讯云），备案通过后签发，下载 Nginx 格式证书包
# 方式 B：服务器上有公网 80 端口且域名已解析，用 certbot：
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d your.domain.com --agree-tos -m you@example.com
# 产出：/etc/letsencrypt/live/your.domain.com/fullchain.pem 与 privkey.pem
```

## 第二步：放置证书到约定路径（路径自文档化）

```bash
cd gflc/deploy
mkdir -p certs && chmod 700 certs
cp /etc/letsencrypt/live/your.domain.com/fullchain.pem certs/fullchain.pem
cp /etc/letsencrypt/live/your.domain.com/privkey.pem   certs/privkey.pem
chmod 600 certs/privkey.pem
cp nginx-ssl.conf.example nginx-ssl.conf
sed -i 's/your.domain.com/你的真实域名/g' nginx-ssl.conf
# 严禁：把 certs/ 或 *.pem 提交 git、打进镜像（backend/.dockerignore 已排除）
```

容器内映射关系（见 `docker-compose.ssl.yml`）：
`./certs/fullchain.pem → /etc/nginx/certs/fullchain.pem`，`./certs/privkey.pem → /etc/nginx/certs/privkey.pem`，
与 `nginx-ssl.conf` 中 `ssl_certificate` / `ssl_certificate_key` 路径一致，均以 `:ro` 只读挂载。

## 第三步：启动 HTTPS 覆盖层

```bash
cd gflc/deploy
# 静态校验（daemon 未启动也能做）
docker compose -f docker-compose.yml -f docker-compose.ssl.yml config --quiet

# 真实启动（需 daemon 运行 + 证书已就位 + .env 已填好）
docker compose -f docker-compose.yml -f docker-compose.ssl.yml up -d --force-recreate
docker compose -f docker-compose.yml -f docker-compose.ssl.yml ps
```

覆盖层做了三件事：① nginx 由 80 改为 80(301) + 443；② `COOKIE_SECURE=true`（Set-Cookie 带 Secure）；
③ CORS 白名单切到 `https://你的域名`。HSTS 在 `nginx-ssl.conf` 中以
`Strict-Transport-Security: max-age=31536000; includeSubDomains` 下发（确认所有子域都可 HTTPS 后再考虑 preload）。

## 第四步：验证（四项全过才算 G3 完成）

```bash
DOMAIN=你的真实域名
# 1) HTTP 应 301 到 HTTPS
curl -sSI http://$DOMAIN/health | head -n 5
# 2) HTTPS 健康接口 200
curl -fsS https://$DOMAIN/health
# 3) Cookie 带 Secure / HSTS 响应头存在
curl -sSI https://$DOMAIN/api/auth/login | grep -iE 'strict-transport-security|set-cookie'
# 4) 浏览器打开 https://$DOMAIN/ 应有锁标志；接口文档应 403
curl -s -o /dev/null -w '%{http_code}\n' https://$DOMAIN/docs      # 期望 403
```

浏览器侧再确认：`Set-Cookie` 含 `Secure; HttpOnly`，地址栏锁标志有效，`/docs`、`/openapi.json` 返回 403。
四项全过 + 证书为可信 CA 签发 → 才可写「G3 已通过」。

---

## 已知边界（外部不可代劳）

- **证书签发**：必须等域名实名 + ICP 备案通过（G7），本机无法代劳。
- **MinIO 预签名直传的 HTTPS**：9000 端口需单独为 MinIO 配证书或经 nginx 反代；本覆盖层刻意不改
  `MINIO_SECURE` / `MINIO_PUBLIC_ENDPOINT`，避免证书未就绪时直传失效。该项随证书到位后一并处理。
- **生产密钥与域名实名**：见 15 号文档「外部不可代劳清单」。
