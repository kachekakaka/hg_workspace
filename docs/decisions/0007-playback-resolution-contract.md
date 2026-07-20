# ADR 0007：先建立 provider-neutral 短期 playback 契约

- 状态：Accepted；媒体代理归属部分由 ADR 0008 修订
- 日期：2026-07-19

## 背景

作品和分集目录已经稳定，但旧播放脚本把 Cookie、Authorization、来源回退、短期 URL 和客户端返回混在一起。直接迁移会让凭据泄露风险、过期策略和代理行为无法审计，也可能把未授权访问误写成产品能力。

## 决策

1. 定义 `PlaybackProvider.resolve(work, episode)`，只返回短期 `PlaybackCandidate`。
2. 候选必须使用 HTTPS、无 URL 凭据、带时区未来 expiry，并通过 header 安全检查。
3. 短期结果写入独立 `playback_resolutions` 表；作品和分集表不保存播放 URL。
4. 无 headers 且 provider 显式允许时可标记 `direct`；存在 headers 时不向客户端返回 URL 或 headers。
5. API 只返回 provider、delivery、mime、expiry 和可选 direct URL，不返回服务端 headers。
6. 默认生产 provider registry 为空；测试通过合成 provider 注入验证契约。
7. provider 原始异常不进入 HTTP 响应，避免内部信息或凭据泄露。
8. 媒体代理的具体归属由后续 ADR 明确。

## 原因

- 先固定数据和安全边界，避免来源实现反向污染 API；
- 短期缓存减少重复解析，同时保留明确 expiry；
- Android 不应直接获得 Cookie、Authorization 或 provider headers；
- 空 registry 诚实反映当前没有生产播放能力。

## 影响

正面：

- Android 和 Web 后续可依赖稳定 response model；
- provider 可以按授权来源独立实现和测试；
- URL、headers 和错误均有集中验证与脱敏；
- 解析缓存可失效、过期和级联删除。

限制：

- 当前生产请求会返回 provider 未配置；
- 带 headers 的候选需要外部代理才能消费；
- SQLite 短期 headers 仅受服务端文件权限保护，部署时必须保护数据卷；
- 不代表任何第三方内容已获得访问、缓存或播放授权。

## 后续修订

ADR 0008 明确：媒体代理由用户 NAS 承担，HG 后端不实现媒体转发、HTTP Range 或固定公网 IP 方案；交付枚举改为 `external_proxy_required`。
