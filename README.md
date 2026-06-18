# PyLocalSend

PyLocalSend 是一个面向局域网的文件传输工具。发送端只登记本机文件或文件夹路径，接收端通过 CLI 或浏览器从发送端流式下载，适合课堂演示、宿舍/实验室内网传文件、临时共享大文件等场景。

项目同时提供命令行和 WebUI：发送端可以用 WebUI 管理共享文件和接收端链接，接收端可以零安装打开链接下载文件。

## 功能特性

- 发送端本地路径注册：只保存绝对路径和元数据，不提前复制文件内容。
- 局域网 HTTP 流式传输：文件边读边发，适合大文件。
- CLI 接收端下载：支持下载目录指定、多文件并行、文件夹递归下载、HTTP Range 断点续传。
- 接收端 WebUI 下载：接收端浏览器直接保存文件；文件夹自动以 ZIP 下载。
- PIN 和接收端 token：支持统一 PIN 验证，也可以为每个接收端生成专属链接。
- 可选 AES-CTR 传输加密：CLI 下载路径支持加密流解密。
- 下载开放控制：发送端通过勾选决定哪些文件/子路径对接收端可见；未开放项在列表和下载接口中均不可访问。
- 接收端禁用/启用：可临时禁止某个 token 链接下载，并立即停止进行中的传输。
- 接收端 WebUI 自动同步：轮询 catalog 版本，发送端变更开放范围后接收端页面自动更新。
- 接收端浏览器上传：发送端可按接收端单独允许或禁止通过浏览器向发送端电脑推送文件；被允许的接收端在 WebUI 中会出现「上传文件」标签页。
- 记录与配置持久化：保存共享文件、开放范围、接收端、下载记录和基础配置。

## 环境要求

- Python 3.10+
- Windows、Linux、macOS 均可运行
- 发送端和接收端需要处在可互相访问的网络中

下面示例以 Windows PowerShell 为主。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

开发和运行测试时安装额外依赖：

```powershell
pip install -e ".[dev]"
```

## 快速开始

### 1. 启动发送端

使用 CLI 服务模式：

```powershell
pylocalsend sender
```

或启动发送端 WebUI：

```powershell
pylocalsend gui
```

如果启用了 PIN 验证且还没有配置 `server_pin`，启动发送端时会自动生成一个 PIN。发送端会显示本机、局域网等可访问地址，例如：

```text
http://192.168.1.100:8765
```

### 2. 注册共享文件

```powershell
pylocalsend upload D:\data\file.zip D:\photos
```

注册操作不会把文件复制到项目目录或缓存目录，只会保存路径、大小、修改时间等信息。可以继续查看、删除和检查状态：

```powershell
pylocalsend ls
pylocalsend rm D:\data\file.zip
pylocalsend status
```

也可以在 `pylocalsend gui` 的“文件传输”页面输入绝对路径并注册。

通过 `grant` 命令管理对接收端的开放范围（与 WebUI 勾选等效）：

```powershell
pylocalsend grant ls
pylocalsend grant close D:\photos\vacation
pylocalsend grant open D:\photos\vacation beach sunset.jpg
pylocalsend grant open-all
```

### 3. 接收端 CLI 下载

每次命令都传入发送端地址和 PIN：

```powershell
pylocalsend ls-remote -H http://192.168.1.100:8765 --pin 123456
pylocalsend download file.zip -d D:\downloads -H http://192.168.1.100:8765 --pin 123456
```

也可以先保存连接信息，再下载：

```powershell
pylocalsend connect -H http://192.168.1.100:8765 --pin 123456
pylocalsend download file.zip -d D:\downloads
```

`download` 支持按文件名或文件 ID 下载。下载文件夹时会递归保存其中的文件，并保持相对目录结构。

### 4. 接收端 WebUI 下载

发送端可以创建接收端记录，并生成带 token 的访问链接：

```powershell
pylocalsend receiver new --name laptop --pin 123456
pylocalsend receiver ls
pylocalsend receiver disable --id <receiver-id>
pylocalsend receiver enable --id <receiver-id>
pylocalsend receiver rm --id <receiver-id>
```

禁用接收端后，该 token 无法下载；若发送端服务正在运行，进行中的传输会被中断。省略 `--id` 时可交互选择。

在 `pylocalsend gui` 的“接收端管理”页面也可以创建接收端并复制链接。接收端打开链接后，可以在浏览器页面中选择文件并下载。

以接收端 token 查看可见文件列表（与 WebUI 所见一致）：

```powershell
pylocalsend ls-remote -H http://192.168.1.100:8765 --pin 123456 --token <token-from-receiver-ls>
```

接收端 WebUI 的下载由浏览器直接处理，文件会保存到当前浏览器的默认下载目录；如果需要每次选择保存位置，请在浏览器设置中开启“下载前询问保存位置”。这样可以避免服务端 Python 进程把文件误写到发送端电脑。

### 5. 接收端浏览器上传

默认情况下，接收端只能下载，不能向发送端电脑上传文件。若需要反向传文件（例如学生交作业、同事回传资料），发送端可在 WebUI「接收端管理」中对某个接收端点击 **「允许上传」**。

被允许上传的接收端打开 `/r/<token>` 链接后，页面会多出 **「上传文件」** 标签页，使用 NiceGUI 上传组件选择文件并上传。上传后的文件会保存到发送端电脑上的存放目录：

```text
{upload_dir}/{接收端名称}/{文件名}
```

- `upload_dir` 可在发送端 WebUI「设置」中配置；留空时默认为 `~/.pylocalsend/browser_uploads`。
- 子目录按**接收端名称**划分，名称中的非法路径字符会自动替换为 `_`。
- 同名文件已存在时，会自动追加时间戳避免覆盖。

**重要：** 接收端上传只会把文件写到发送端磁盘，**不会**自动加入发送端「文件传输」共享列表，也不会自动对接收端开放下载。发送端若要把这些文件共享出去，需在「文件传输」中手动填写路径（文件或所在文件夹）并点击「确认上传」注册，再按需勾选开放范围。

在「接收端管理」中点击 **「禁止上传」** 可收回上传权限；接收端被禁用时，上传和下载均不可用。

## 常用命令

```powershell
# 启动发送端
pylocalsend sender --no-browser   # cli 后台服务，无 WebUI
pylocalsend gui                   # 启动发送端 WebUI

# 注册和管理共享文件
pylocalsend upload <file-or-dir> [...]
pylocalsend ls
pylocalsend rm <file-or-dir> [...]
pylocalsend grant ls [item]
pylocalsend grant open <item> [subpath ...]
pylocalsend grant close <item> [subpath ...]
pylocalsend grant open-all
pylocalsend grant close-all

# 接收端连接和下载
pylocalsend ls-remote -H <sender-url> --pin <pin> [--token <token>]
pylocalsend connect -H <sender-url> --pin <pin>
pylocalsend download <name-or-id> [...] -d <dest-dir> [--token <token>]

# 接收端链接
pylocalsend receiver new --name <name> --pin <pin>
pylocalsend receiver ls
pylocalsend receiver disable [--id <receiver-id>]
pylocalsend receiver enable [--id <receiver-id>]
pylocalsend receiver rm --id <receiver-id>

# 配置
pylocalsend config-show
pylocalsend config-show --key port
pylocalsend config-set --key port 8765
```

## WebUI 说明

### 发送端 WebUI

`pylocalsend gui` 会打开发送端管理页面，主要包含三个模块：

- 文件传输：注册文件或文件夹、查看共享列表、展开文件夹内容、删除共享项、查看下载记录。首列复选框控制「是否对接收端开放下载」，支持子文件夹/子文件级联勾选；工具栏提供「全部开放 / 全部关闭」。新注册项默认全部开放。此处「上传」指登记本机绝对路径，与接收端浏览器上传不同。
- 接收端管理：创建接收端、生成专属链接、复制链接、允许/禁止浏览器上传、禁用/解除禁用接收端、删除接收端、查看下载记录。列表显示接收端状态（正常/已禁用）和上传权限（已允许/未允许）。禁用后该链接无法下载或上传，进行中的下载会被中断。
- 设置：查看和修改分片大小、浏览器上传存放路径等配置；也可通过 CLI 修改端口、并行数、PIN 验证、加密开关等。

### 接收端 WebUI

接收端通过 `/r/<token>` 链接访问页面。

**文件下载**（所有接收端均有）：

- 仅列出发送端已勾选开放的文件和文件夹，并约每 2 秒检测 catalog 版本变化，自动同步最新列表。
- 单文件下载：浏览器直接请求发送端下载接口并保存。
- 文件夹下载：发送端按开放范围流式打包 ZIP，浏览器保存为 `<文件夹名>.zip`。
- 下载位置：由接收端浏览器决定，不由发送端服务器写入本地路径。
- 若接收端已被发送端禁用，页面会提示且禁止下载。

**上传文件**（仅发送端已「允许上传」的接收端可见）：

- 使用 NiceGUI 上传组件，支持多文件、选择后自动上传。
- 文件写入发送端电脑上配置的存放目录，按接收端名称分子文件夹。
- 上传成功不会自动出现在发送端共享列表；需由发送端手动注册路径后才会对其他接收端开放下载。
- 接收端被禁用时，上传组件不可用。

## 配置

配置文件保存在用户目录下的 `.pylocalsend` 文件夹中。当前支持的配置项包括：

- `host`：发送端绑定地址，默认 `0.0.0.0`。
- `port`：发送端端口，默认 `8765`。
- `chunk_size`：流式读写分片大小。
- `max_parallel`：CLI 下载并行数。
- `encryption_enabled`：是否启用 AES-CTR 加密流。
- `pin_verification_enabled`：是否启用 PIN 验证。
- `server_pin`：发送端 PIN。
- `upload_dir`：接收端浏览器上传的存放根目录。留空时使用 `~/.pylocalsend/browser_uploads`；实际文件保存在其下的 `{接收端名称}/` 子目录中。

查看和修改配置：

```powershell
pylocalsend config-show
pylocalsend config-show --key port
pylocalsend config-set --key port 8765
pylocalsend config-set --key encryption_enabled true
pylocalsend config-set --key upload_dir D:\pylocalsend-uploads
```

也可以在 `pylocalsend gui` 的「设置」页面直接填写「浏览器上传存放路径」并保存；保存时会尝试创建该目录。

## 项目结构

```text
pylocalsend/
  cli/                 # 命令行入口
  core/
    file_handler/      # 文件元数据、目录遍历、分片读写、download_grants
    receiver/          # 接收端客户端逻辑
    transfer/          # 发送端 HTTP 服务和下载接口
    utils/             # 配置、数据库、加密、网络工具
  gui/
    sender/            # 发送端 NiceGUI 页面
    receiver/          # 接收端 WebUI 页面
tests/                 # 自动化测试
doc/                   # 展示文档和课件
```

## 设计要点

发送端不会提前复制共享文件，只保存路径并在下载时读取原文件。CLI 下载走 `ReceiverClient`，可以控制目标目录、并行度、断点续传和加密解密；接收端 WebUI 走浏览器原生下载，优点是零安装和直观，限制是保存位置由浏览器管理。

文件夹在 CLI 中按目录结构递归下载，在 WebUI 中以 ZIP 流下载。ZIP 流不会先落盘成临时压缩包，而是一边读取文件夹内容一边返回给浏览器。

发送端通过 `download_grants` 表记录每个共享项的开放路径（空字符串 `''` 表示整项开放）。接收端 token 访问时，列表、目录树、单文件下载和 ZIP 打包都会按 grants 过滤。catalog 版本由共享文件与 grants 内容哈希生成，供接收端 WebUI 轮询检测变更。

接收端浏览器上传与发送端路径注册是两条独立链路：上传只写磁盘，注册才进入 `files` 表并参与共享与 grants。这样发送端可以先把文件收到本地，再决定是否、以及如何开放给接收端下载。

相关 HTTP API（需 PIN 或 token 鉴权）：

- `GET /api/files/catalog-version` — 返回当前 catalog 版本号
- `POST /api/files/browser-upload` — 接收端浏览器上传（需 token 且该接收端已允许上传）
- `POST /api/receivers/{id}/allow-upload` — 允许接收端浏览器上传
- `POST /api/receivers/{id}/disallow-upload` — 禁止接收端浏览器上传
- `POST /api/receivers/{id}/disable` — 禁用接收端
- `POST /api/receivers/{id}/enable` — 解除禁用

## 测试

```powershell
pytest tests -v
```

如果只想运行某个测试文件：

```powershell
pytest tests\test_cli.py -v
```

## 注意事项

- 发送端和接收端需要能访问同一个局域网地址；公网访问需要自行配置路由器端口映射。
- WebUI 浏览器下载不能像 CLI 一样直接写入任意绝对路径，这是浏览器安全限制。
- CLI 下载更适合大批量、断点续传、精确指定保存目录的场景；WebUI 更适合临时接收和课堂演示。
- 接收端浏览器上传会把文件写到发送端磁盘；若需共享，发送端仍需在「文件传输」中手动注册路径。上传目录可通过 `upload_dir` 配置或 WebUI 设置修改。
