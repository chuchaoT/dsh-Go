# iOS 自用侧载（含本机引擎）设计

日期：2026-11-13  
分支基线：`feat/ios-foundation`  
状态：仓库侧交付已落地（`docs/ios-sideload.md`）。装到手机仍要在你的 fork 上跑 `iOS compile` 再侧载。

## 1. 目标与非目标

### 目标

在 `feat/ios-foundation` 上，打出**带本机引擎**的包，装到用户自己的 iPhone/iPad 上日用。

「部署成功」的最小标准：

1. App 冷启动正常（不白屏、不秒崩）
2. 能安装并启动本机引擎；配置模型后跑完一轮（写文件 / 搜索 / bash，含真实审批）
3. 停止后再启动，无需杀掉 App
4. 远程连接仍可用（引擎失败时的兜底）

### 非目标（第一版不做）

- App Store / TestFlight 上架
- APNs（离开应用后的推送提醒）
- 桌宠悬浮窗、应用内更新（iOS 本就没有）
- 手机操控端上 self-runner / Mac XCTest 路径的完备验收
- 可选 Linux guest（iSH）作为上线门槛（可后装）
- 向官方上游提外部 PR（上游暂不接受）
- 付费 Apple Developer 证书流水线（除非用户自行后续加）

## 2. 约束

| 约束 | 处理 |
|---|---|
| 开发机是 Windows，无 Mac | 编译只走 GitHub Actions macOS runner |
| 无付费开发者账号（默认） | CI 产出**未签名** IPA；Windows 用 Sideloadly（或同类）+ Apple ID 重签侧载 |
| 免费账号约 7 天 / 约 3 台设备 | 文档写明重签周期；侧载失败时优先去掉 ShareExtension |
| 上游不收外部 PR | 工作在用户自己的 **fork** 上触发 Actions |
| 嵌套原生 framework 必须被重签 | 侧载工具须签主 App 与 `Frameworks/*.framework`；文档强调，失败时按引擎加载错误排查 |

## 3. 出包链路

```
用户 fork（feat/ios-foundation 或 feat/ios-* / ios/**）
  → workflow「iOS compile」（已有）
  → engine job：prepare-engine + 真机用未签名 archive
  → artifact：ios-unsigned-ipa（保留约 14 天）
  → Windows 下载
  → Sideloadly 等用 Apple ID 重签并安装
  → 按最小验收表测试
```

现有依据：

- `.github/workflows/ios-compile.yml`：`push` 到 `feat/ios-**` / `ios/**`，或 `workflow_dispatch`
- `tooling/ios/check-archive.sh`：产出 `$RUNNER_TEMP/DSH-Go-unsigned.ipa`，注释写明需事后签名再装机
- artifact 名：`ios-unsigned-ipa`

运行时形态（沿用分支，不新造架构）：

- Flutter UI + Swift MethodChannel
- 同进程 NodeMobile（`--jitless`）作本机 DSH 引擎（与鸿蒙共用 `runtime/ohos/` 基础层）
- 可选 iSH Linux guest：第一版不挡上线
- 远程主机连接保留

## 4. 改动范围

### 会做

1. **文档**：新增 `docs/ios-sideload.md`（中文为主；需要时补英文短链）。内容：fork → 开 Actions → 触发 CI → 下载 `ios-unsigned-ipa` → Sideloadly 重签（含嵌套 framework）→ 最小验收 → 常见失败
2. **侧载友好配置**：默认文档给出「去掉 ShareExtension + 两份 App Group entitlements」的手工步骤；若步骤易错再加 `tooling/ios/` 下可在 Windows 跑的小脚本改 `project.pbxproj`（不引入新 CI job）
3. **Bundle ID**：在 `docs/ios-sideload.md` 写清占用时要改的位置（Runner / ShareExtension / entitlements / ShareInbox group）；第一版不改仓库默认 ID，侧载撞车后再改
4. **CI 使用说明**：写在同一指南里；确认 fork 上 `workflow_dispatch` 与 `feat/ios-**` / `ios/**` 触发规则；不改上游 workflow 语义，除非发现 fork 无法触发的硬缺陷
5. **真机坑检查项**：framework 布局、引擎 addon 加载、未重签嵌套库等，写入 `docs/ios-sideload.md`（对齐 `app/ios/README.md` 现状，不复制整份验收表）

### 不做

- 大改引擎 / NodeMobile / iSH
- 补齐手机操控、Siri 真机、后台继续（iOS 26）等非最小日用项
- 在 Windows 上假装完成本地 `flutter build ios`

### 工作仓库

用户 fork。本地可基于已检出的 `feat/ios-foundation` 改；用户推送到 fork 后触发 CI。

## 5. 实施顺序

### Phase 0（用户，约 10 分钟）

1. Fork `ccch1mneyyy/dsh-Go`
2. 在 fork 打开 Actions
3. 推送/同步 `feat/ios-foundation`（可在 Phase 1 文档与补丁合入后再推）

### Phase 1（Windows / 本代理）

1. 撰写 `docs/ios-sideload.md`
2. 落地「无 ShareExtension」文档步骤（必要时再加 Windows 可跑脚本）
3. 对照 `ios-compile.yml` 与 `check-archive.sh` 核对 artifact 名与触发条件

### Phase 2（用户）

手动 `workflow_dispatch` 或 push 触发 `iOS compile` → 等 **engine** 成功 → 下载 `ios-unsigned-ipa`

### Phase 3（用户 + 反馈）

侧载 → 最小验收 → 失败时提供系统版本与现象 → 再针对性改（Bundle ID、扩展剥离、文档补充）

### Phase 4（以后）

可选 guest、手机操控、推送等，不挡第一版。

## 6. 风险与回退

| 风险 | 缓解 |
|---|---|
| 侧载后引擎因未重签 framework 加载失败 | 指南强调嵌套签名；失败时先用远程连接日用 |
| 免费账号无法注册 App Group | 去掉 ShareExtension；仅少系统分享入口 |
| Bundle ID 被占用 | 按文档改三处（或两处，若已无扩展） |
| CI 分钟耗尽 / queue 排队 | 保留 `workflow_dispatch`；必要时缩小路径触发后的无效重跑 |
| fork 默认关闭 Actions | Phase 0 明确要求打开 |

回退：任意阶段引擎不可用时，同一 App 仍可只连远程主机。

## 7. 测试与验收

### CI（已有，不新造门禁除非发现缺口）

- `iOS compile` 的 compile + engine（含 prepare-engine、模拟器烟测、unsigned ipa artifact）

### 真机最小验收（用户执行）

见第 1 节四条。详细扩展项仍以 `app/ios/README.md`「真机验收」表为参考，但不作为第一版完成条件。

## 8. 决策记录

| 决策 | 选择 |
|---|---|
| 产品范围 | 完整本机引擎（方案 B），非仅远程 |
| 编译环境 | 无 Mac → 用仓库现有 GitHub Actions |
| 安装方式 | 未签名 IPA + Windows 侧载，不上架 |
| 基线分支 | `feat/ios-foundation` |
| 协作方式 | 用户 fork，不向上游开外部 PR |
