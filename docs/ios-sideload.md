# 把带本机引擎的 DSH Go 装到自己的 iPhone

没有 Mac 时，用你自己的 GitHub fork 跑已有的 `iOS compile`，下载未签名安装包，再在 Windows 上用 Sideloadly 和免费 Apple ID 装到手机。不上架。

基线是分支 `feat/ios-foundation`。`main` 没有 `app/ios`，推 `main` 打不出这个包。

英文要点在文末。

## 怎样算装好了

1. 冷启动能进主界面，不白屏、不马上退出。
2. 设置里装好本机运行环境并启动；配好模型后，新对话能写文件、搜索、跑一条 bash，审批是真的弹出来的。
3. 停止引擎后再启动，不用划掉 App。
4. 引擎起不来时，仍能连一台远程主机接着聊天。

可选 Linux、手机操控、Siri、离开 App 后的推送，都不算这一步的完成条件。离开 App 后系统会暂停本机引擎；锁屏提醒要 APNs，还没做。

## 1. Fork 并打开 Actions

1. 打开 <https://github.com/ccch1mneyyy/dsh-Go>，点 Fork。上游暂不收外部 PR，编译只在你自己的 fork 上跑。
2. 在 fork 的 Settings → Actions → General 里允许 Actions。第一次还要在 Actions 页点启用。
3. 把 `feat/ios-foundation` 推到 fork。本地这份检出已经在该分支上。

只改 `docs/` 不会开始编译。`iOS compile` 在 push 时只看这些路径：`app/**`、`packages/**`、`tooling/ios/**`、`runtime/ios/**`、`runtime/ohos/**`、`runtime/patches/**`、`.github/workflows/ios-compile.yml`。分支名还要匹配 `feat/ios-**` 或 `ios/**`。手动运行不受路径限制。

## 2. 免费 Apple ID：先去掉分享扩展

安装包默认带着分享扩展，并且 `Runner` 与分享扩展的 entitlements 都声明了 App Group `group.io.github.ccch1mneyyy.dshgo`。免费账号经常注册不了 App Group，Sideloadly 会在签名这一步失败。

在仓库根目录执行：

```bash
python tooling/ios/strip-share-extension.py
```

它会改三个文件：

- `app/ios/Runner.xcodeproj/project.pbxproj`：去掉 ShareExtension 目标、嵌入阶段和依赖。主 App 仍编译 `ShareInbox.swift` 和 `ShareChannel.swift`。
- `app/ios/Runner/Runner.entitlements`
- `app/ios/ShareExtension/ShareExtension.entitlements`

两份 entitlements 里的 `com.apple.security.application-groups` 会被删掉。`app/ios/PhoneRunner/PhoneRunner.entitlements` 故意不动，那个目标不进安装包。再跑一次会打印 `already stripped`。

少掉的是系统分享入口（从 Safari 分享进 App）。聊天、本机引擎、远程连接还在。

把这三个文件提交并推到 `feat/ios-foundation`（或任意 `feat/ios-*`）。这次 push 改了 `app/**`，会触发编译。

## 3. 跑编译并下载安装包

在 fork 的 Actions 里打开 **iOS compile**。push 已经触发的话等那次；否则选 `workflow_dispatch`，分支选 `feat/ios-foundation`，Run workflow。

要等名为 **engine** 的 job 成功。它会先跑 `tooling/ios/prepare-engine.sh`（NodeMobile 和本机引擎），再由 `tooling/ios/check-archive.sh` 打出未签名包。旁边的 `compile` job 不上传这个安装包。

下载 artifact **`ios-unsigned-ipa`**。里面是 `DSH-Go-unsigned.ipa`。Artifact 保留 14 天，下载后自己留一份。`engine` 没绿灯就不要装。

解压后应能看到 `Payload/Runner.app/Frameworks/` 里这些目录，名字与 `check-archive.sh` 一致：

- `DshNodeHost.framework`
- `DshFlock.framework`
- `DshRequireBuiltin.framework`
- `DshGuest.framework`
- `DshGuestBridge.framework`

缺任意一个，说明下到的不是带引擎的那份包。

## 4. 在 Windows 上装到手机

手机系统需能装这个工程（最低 iOS 15）。iOS 16 及以上要打开「设置 → 隐私与安全性 → 开发者模式」，然后重启。用数据线连上电脑并信任这台电脑。Windows 上要有 Sideloadly，以及苹果设备支持（iTunes 或「Apple 设备」应用）。

1. 把 `DSH-Go-unsigned.ipa` 拖进 Sideloadly。
2. 填免费 Apple ID。签名大约 7 天有效，过期后用同一份 IPA 再签一次。一台免费账号大约只能登记 3 台设备。
3. 安装时让工具签整个 App，包括 `Frameworks` 里每一个 `.framework`。只签最外层的 `Runner` 时，手机上能打开界面，本机引擎会在加载没签名的 addon 时失败。2026-11-06 的 iPad 记录就是这种失败；addon 已改成 framework，侧载时仍要逐个签上。
4. 装完后在手机上打开「设置 → 通用 → VPN 与设备管理」，信任刚才的开发者描述文件。

Bundle ID 默认是 `io.github.ccch1mneyyy.dshgo`。被占用时再改，不要提前改。要一起改的位置：

| 位置 | 现在的值 |
|---|---|
| `project.pbxproj` 里 Runner 的 `PRODUCT_BUNDLE_IDENTIFIER` | `io.github.ccch1mneyyy.dshgo` |
| 同文件里 ShareExtension 的 `PRODUCT_BUNDLE_IDENTIFIER`（剥离之后这条已经不在） | `io.github.ccch1mneyyy.dshgo.ShareExtension` |
| `Runner.entitlements`、`ShareExtension.entitlements` 的 App Group | `group.io.github.ccch1mneyyy.dshgo` |
| `app/ios/ShareExtension/ShareInbox.swift` 的 `group` | 同上 |
| `app/ios/Runner/IOSPhoneRunner.swift` 和 `app/ios/PhoneRunner/PhoneRunnerUITests.swift`、`PhoneRunner.entitlements` | 同一组 ID。手机操控不在这一步的验收里，但改主 App 的组 ID 时这三处要一起改，避免以后接回去对不上 |

扩展的 Bundle ID 必须以主 App 的 ID 开头。改完再推分支，重新下 IPA。

## 5. 装好后检查

按上面四条做一遍。引擎页可以安装本机运行环境；中途杀掉 App 再打开，应能接着装完。第一次启动引擎才会加载 Node，只连远程时不会多占那一块内存。

引擎加载失败时，先确认侧载工具签过 `Frameworks` 里那五个 framework，再看是不是装成了没有 `engine` job 产物的包。在这之前用远程主机继续用。

## 不会发生的事

- 这份未签名 IPA 不能直接装，必须由 Sideloadly（或会签嵌套 framework 的同类工具）重签。
- 没有 APNs，App 不在前台时，等你确认的请求不会响。
- 桌宠悬浮窗和应用内更新在 iOS 上没有。
- 这里不跑 `flutter build ios`。Windows 上编译成功不能当作已经装上手机。

## English

Fork `ccch1mneyyy/dsh-Go`, push `feat/ios-foundation`, and enable Actions. A docs-only push does not start **iOS compile**; `workflow_dispatch` does. For a free Apple ID, run `python tooling/ios/strip-share-extension.py`, commit, and push. Download artifact `ios-unsigned-ipa` only after the **engine** job is green (`DSH-Go-unsigned.ipa`, kept 14 days). Sideloadly must sign `Runner` and every framework under `Payload/Runner.app/Frameworks` (`DshNodeHost`, `DshFlock`, `DshRequireBuiltin`, `DshGuest`, `DshGuestBridge`). A signature lasts about 7 days. Done means: the app launches, the on-device engine finishes one approved tool round, it restarts without killing the app, and a remote host still connects.
