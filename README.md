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
- 记录与配置持久化：保存共享文件、接收端、下载记录和基础配置。

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
pylocalsend receiver rm --id <receiver-id>
```

在 `pylocalsend gui` 的“接收端管理”页面也可以创建接收端并复制链接。接收端打开链接后，可以在浏览器页面中选择文件并下载。

接收端 WebUI 的下载由浏览器直接处理，文件会保存到当前浏览器的默认下载目录；如果需要每次选择保存位置，请在浏览器设置中开启“下载前询问保存位置”。这样可以避免服务端 Python 进程把文件误写到发送端电脑。

## 常用命令

```powershell
# 启动发送端
pylocalsend sender
pylocalsend gui

# 注册和管理共享文件
pylocalsend upload <file-or-dir> [...]
pylocalsend ls
pylocalsend rm <file-or-dir> [...]

# 接收端连接和下载
pylocalsend ls-remote -H <sender-url> --pin <pin>
pylocalsend connect -H <sender-url> --pin <pin>
pylocalsend download <name-or-id> [...] -d <dest-dir>

# 接收端链接
pylocalsend receiver new --name <name> --pin <pin>
pylocalsend receiver ls
pylocalsend receiver rm --id <receiver-id>

# 配置
pylocalsend config-show
pylocalsend config-show --key port
pylocalsend config-set --key port 8765
```

## WebUI 说明

### 发送端 WebUI

`pylocalsend gui` 会打开发送端管理页面，主要包含三个模块：

- 文件传输：注册文件或文件夹、查看共享列表、展开文件夹内容、删除共享项、查看下载记录。
- 接收端管理：创建接收端、生成专属链接、复制链接、删除接收端、查看下载记录。
- 设置：查看和修改端口、分片大小、并行数、PIN 验证、加密开关等配置。

### 接收端 WebUI

接收端通过 `/r/<token>` 链接访问页面。页面会列出发送端已共享的顶层文件和文件夹：

- 单文件下载：浏览器直接请求发送端下载接口并保存。
- 文件夹下载：发送端按需流式打包 ZIP，浏览器保存为 `<文件夹名>.zip`。
- 下载位置：由接收端浏览器决定，不由发送端服务器写入本地路径。

## 配置

配置文件保存在用户目录下的 `.pylocalsend` 文件夹中。当前支持的配置项包括：

- `host`：发送端绑定地址，默认 `0.0.0.0`。
- `port`：发送端端口，默认 `8765`。
- `chunk_size`：流式读写分片大小。
- `max_parallel`：CLI 下载并行数。
- `encryption_enabled`：是否启用 AES-CTR 加密流。
- `pin_verification_enabled`：是否启用 PIN 验证。
- `server_pin`：发送端 PIN。

查看和修改配置：

```powershell
pylocalsend config-show
pylocalsend config-show --key port
pylocalsend config-set --key port 8765
pylocalsend config-set --key encryption_enabled true
```

## 项目结构

```text
pylocalsend/
  cli/                 # 命令行入口
  core/
    file_handler/      # 文件元数据、目录遍历、分片读写
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
