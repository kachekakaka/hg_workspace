# ADR 0007：先建立 provider-neutral 短期 playback 契约

- 状态：Accepted
- 日期：2026-07-19

## 背景

作品和分集目录已经稳定，但旧播放脚本把 Cookie、Authorization、来源回退、短期 URL 和客户端返回混在一起。直接迁移会让凭据泄露风险、过期策略和代理行为无法审计，也可能把未授权访问误写成产品能力。

## 决策

1. 定义 `PlaybackProvider.resolve(work, episode)`，只返回短期 `PlaybackCandidate`。
2. 候选必须使用 HTTPS、无 URL 凭据、带时区未来 expiry，并通过 header 安全检查。
3. 短期结果写入独立 `playback_resolutions` 表；作品和分集表不保存播放 URL。
4. 无 headers 且 provider 显式允许时可标记 `direct`；存在 headers 时只标记 `proxy_required`，不向客户端返回 URL 或 headers。
5. API 只返回 provider、delivery、mime、expiry 和可选 direct URL，不返回服务端 headers。
6. 默认生产 provider registry 为空；测试通过合成 provider 注入验证契约。
7. provider 原始异常不进入 HTTP 响应，避免内部信息或凭据泄露。
8. proxy、HTTP Range、header 注入、日志脱敏和媒体缓存留到后续独立批次。

## 原因

- 先固定数据和安全边界，避免来源实现反向污染 API；
- 短期缓存减少重复解析，同时保留明确 expiry；
- `proxy_required` 允许后续在服务端安全附加 headers，而不是交给 Android；
- 空 registry 诚实反映当前没有生产播放能力。

## 影响

正面：

- Android 和 Web 后续可依赖稳定 response model；
- provider 可以按授权来源独立实现和测试；
- URL、headers 和错误均有集中验证与脱敏；
- 解析缓存可失效、过期和级联删除。

限制：

- 当前生产请求会返回 provider 未配置；
- `proxy_required` 暂时没有可消费的媒体 endpoint；
- SQLite 短期 headers 仅受服务端文件权限保护，部署时必须保护数据卷；
- 不代表任何第三方内容已获得访问、缓存或播放授权。
