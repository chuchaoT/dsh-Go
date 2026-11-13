# iOS 自用侧载 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `feat/ios-foundation` 上交出 Windows 可核对的自用侧载材料：部署指南，以及可选地从工程里去掉分享扩展和两份 App Group，使 GitHub Actions 打出的未签名 IPA 能用免费 Apple ID 装到自己的手机。

**Architecture:** 不新造编译流水线。安装包仍由已有的 `iOS compile` workflow 里 `engine` job 调用 `tooling/ios/check-archive.sh` 产出 `ios-unsigned-ipa`。默认工程保持分享扩展；免费账号注册不了 App Group 时，先在 Windows 上跑剥离脚本，再把改过的工程推上 fork 重新编译。

**Tech Stack:** 现有 GitHub Actions（`macos-26`、Flutter 3.47.7）、`project.pbxproj`、XML entitlements、Python 3 标准库。

## Global Constraints

- 基线分支是 `feat/ios-foundation`。
- 编译只走 GitHub Actions，不在 Windows 上执行 `flutter build ios`。
- 产物名是 `ios-unsigned-ipa`，文件是 `DSH-Go-unsigned.ipa`，保留 14 天。
- `push` 触发分支是 `feat/ios-**` 与 `ios/**`，且只在 `app/**`、`packages/**`、`tooling/ios/**`、`runtime/ios/**`、`runtime/ohos/**`、`runtime/patches/**`、`.github/workflows/ios-compile.yml` 有改动时跑；`workflow_dispatch` 不受路径限制。
- 第一版不改默认 Bundle ID `io.github.ccch1mneyyy.dshgo`。
- 不新增 CI job，不向上游开 PR。
- 去掉的是分享扩展目标，以及 `Runner.entitlements` 与 `ShareExtension.entitlements` 里的 App Group。`PhoneRunner.entitlements` 留在仓库里，它不进安装包。

---

### Task 1: 部署指南

**Files:**
- Create: `docs/ios-sideload.md`
- Modify: `app/ios/README.md`（免费账号那段加一处指向）

**Interfaces:**
- Consumes: `.github/workflows/ios-compile.yml` 的触发条件与 artifact 名；`tooling/ios/check-archive.sh` 要求的五个 framework 名
- Produces: 用户按文档能 fork、开 Actions、下载 `ios-unsigned-ipa`、用 Sideloadly 安装，并知道最小验收四条

- [x] **Step 1:** 写出中文指南，文末附英文短节。写明只改 `docs/` 不会触发编译。
- [x] **Step 2:** 在 `app/ios/README.md` 免费账号段落加上指南路径。
- [x] **Step 3:** 用检索核对指南里的 workflow 名、分支过滤、artifact 名、framework 名与脚本一致。

### Task 2: 剥离分享扩展

**Files:**
- Create: `tooling/ios/strip-share-extension.py`
- Test: `tooling/ios/tests/strip-share-extension.test.py`

**Interfaces:**
- Consumes: `app/ios/Runner.xcodeproj/project.pbxproj`，两份 entitlements
- Produces: `strip(root) -> None`。跑完后工程里没有 `com.apple.product-type.app-extension`，Runner 仍编译 `ShareInbox.swift`，两份 entitlements 没有 `com.apple.security.application-groups`，`PhoneRunner.entitlements` 不变。再跑一次不改文件。

- [x] **Step 1:** 写测试：临时副本上调用脚本前，扩展目标仍在。
- [x] **Step 2:** 实现脚本。只删扩展目标、嵌入阶段、依赖和对应构建对象；保留 `ShareInbox.swift` / `ShareChannel.swift` 在主 App 源码里。
- [x] **Step 3:** 跑 `python tooling/ios/tests/strip-share-extension.test.py -v`，已通过。默认 `project.pbxproj` 未改。
