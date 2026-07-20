# ADR 0011：Android 先消费 playback 契约，不提前启动播放器

- 状态：Accepted
- 日期：2026-07-20

## 背景

后端已经提供 provider-neutral playback resolution，但 production provider registry 默认为空；带服务端 headers 的内容还需要用户 NAS 的外部代理 handoff。此时直接引入 Media3 或显示“播放”按钮，会把尚未可用的链路误写成产品能力。

## 决策

1. Android 连接时读取 `GET /api/v1/playback/providers`，只对已配置来源提供“检查播放能力”。
2. 使用 `POST /api/v1/episodes/{episode_id}/playback/resolve` 获取短期响应。
3. 客户端只接受 `direct` 和 `external_proxy_required`，拒绝旧 `proxy_required`。
4. `direct` 必须带 HTTPS、无 URL 凭据和 fragment；客户端当前不展示 URL，也不启动播放器。
5. `external_proxy_required` 必须不带 URL，只显示需要 NAS handoff。
6. episode ID 必须与当前分集一致；provider、expiry 和 MIME 需通过基本安全校验。
7. UI 只显示交付模式、provider、缓存状态、MIME 和过期时间。
8. 不引入 Media3、下载服务或 NAS 厂商 API。

## 原因

- 先验证客户端和后端契约，减少播放器批次同时处理数据、安全和媒体生命周期的风险；
- provider 列表让空 production registry 被诚实呈现；
- 不显示 URL 可以避免短期地址被误当成稳定下载链接；
- external 模式保持 NAS 职责边界，不把 headers 下发 Android。

## 影响

正面：

- 后续 Media3 可以直接复用已验证的 `PlaybackResolution`；
- 非法或旧协议响应会在播放器接入前被发现；
- 无 provider 的部署不会显示虚假播放能力。

限制：

- 本批次不能播放任何媒体；
- production provider 与 NAS handoff 仍是前置依赖；
- 未验证真实短期 URL、设备解码或网络切换。
