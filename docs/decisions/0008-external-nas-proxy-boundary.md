# ADR 0008：媒体代理由外部 NAS 承担

- 状态：Accepted
- 日期：2026-07-20

## 背景

ADR 0007 使用 `proxy_required` 表示某些播放候选需要服务端请求头，但尚未实现媒体 endpoint。部署目标随后明确：公网入口和媒体代理由用户自己的 NAS 负责，HG 后端不应再建设一套固定公网 IP、DNS pinning、HTTP Range 和视频字节转发实现。

## 决策

1. 将 API 交付声明改为 `direct` 或 `external_proxy_required`。
2. `direct` 仍只适用于 HTTPS、无 provider headers 且 provider 明确允许的短期 URL。
3. `external_proxy_required` 不返回来源 URL 或 provider headers；它只说明当前候选不能由客户端直接消费。
4. HG 后端不提供 `/stream`、`/proxy` 或媒体转发 endpoint，不承担 Range、带宽、连接复用、TLS 终止和公网暴露。
5. 用户 NAS 负责反向代理、域名/TLS 和需要时的媒体代理。
6. NAS 与后端之间的鉴权、URL 签名和短期凭据交换必须在接口明确后另立 ADR；本批次不猜测 NAS 厂商或 API。
7. 后端短期 SQLite 解析记录继续保留，便于未来建立最小的受控 NAS handoff，但它不是媒体缓存。

## 原因

- 避免在应用内重复实现 NAS 已提供的代理、证书和网络运维能力；
- 降低 SSRF、DNS rebinding、Range 和大流量连接带来的安全与维护负担；
- 保持 Android 不接触 Cookie、Authorization 和 provider headers；
- 不把尚未定义的 NAS 接口伪装成已经可播放的能力。

## 影响

正面：

- 后端范围收缩为目录、任务、解析和安全交付契约；
- 不需要固定公网 IP；
- 部署拓扑更符合 NAS 常驻运行环境；
- 后续 Android 可分别处理 direct 和 NAS 代理 URL。

限制：

- `external_proxy_required` 在 NAS 对接完成前不可播放；
- 当前没有生产 playback provider；
- 服务端媒体缓存与下载的责任边界仍待 NAS 对接协议确定；Android Media3 离线下载仍是客户端目标；
- 只处理有权访问、播放和下载的内容，不绕过任何访问控制。
