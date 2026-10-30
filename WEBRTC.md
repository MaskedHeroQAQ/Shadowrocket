# 独立 WebRTC 规则集

发布地址：<https://raw.githubusercontent.com/MaskedHeroQAQ/Shadowrocket/personal/rulesets/webrtc.yaml>

仅提取 [Niklaus88/Clash-Config](https://github.com/Niklaus88/Clash-Config) 的 `clash-ios-script.js` 中目标为 `WebRTC防护` 的规则，移除策略名称，生成 Clash/Mihomo 的 classical YAML 规则集。MIT 许可原文见 `rulesets/LICENSE-Niklaus88.txt`。

GitHub Actions 每六小时检查一次（北京时间 02:17、08:17、14:17、20:17），也可手动运行 `Sync standalone WebRTC rules`。流程与原小火箭资产同步共用并发组，只有规则内容变化才提交；`webrtc-source.json` 记录最近一次规则变化所用的源版本。工作流不执行下载来的 JavaScript。

只接受有限的端口和 STUN/TURN 专用域名条件，保留标准端口 3478、5349。上游结构变化、空结果、过宽条件或未知类型将报错，失败的任务不会提交，已发布版本继续保留。未同步原脚本的 DNS、策略组、会议例外、广告或系统更新拦截规则。

3x-ui 统一订阅应引用该文件，并在国内直连规则之前匹配：

```yaml
rule-providers:
  webrtc:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/MaskedHeroQAQ/Shadowrocket/personal/rulesets/webrtc.yaml
    path: ./ruleset/webrtc.yaml
    interval: 43200
rules:
  - RULE-SET,webrtc,WebRTC防护
```

`WebRTC防护` 策略组由订阅定义，默认拒绝，可按通话需要选择代理；不提供直连选项。规则集地址不包含节点凭据。原小火箭配置、模块与合并基线保持独立。

这些规则只覆盖已列出的端口和域名，不是 STUN 协议识别，不能保证阻断任意 WebRTC 探测。拦截可能影响通话或 P2P。Clash 的资源刷新受设备休眠、网络和预编译机制影响，发布成功不等于所有设备已经加载；需要在 iPhone 的 Wi-Fi 与蜂窝网络分别复测。GitHub 定时任务可能延迟；公开仓库 60 天无活动会停用定时任务，应结合已有每日巡检检查。
