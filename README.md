# PyLocalSend

PyLocalSend 是一个局域网文件传输工具，提供命令行和发送端 WebUI。发送端只登记本地文件或文件夹路径，接收端通过 HTTP API 下载。

## 环境要求

- Python 3.10+
- Windows、Linux、macOS 均可运行；下面示例以 Windows PowerShell 为主。

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

使用命令行服务模式：

```powershell
pylocalsend sender
```

或启动发送端 WebUI：

```powershell
pylocalsend gui
```

如果启用了 PIN 验证且还没有配置 `server_pin`，启动发送端时会自动生成一个 PIN。

### 2. 注册共享文件

```powershell
pylocalsend upload D:\data\file.zip D:\photos
```

注册只是保存本地绝对路径和元数据，不会复制文件。可以查看和移除已注册路径：

```powershell
pylocalsend ls
pylocalsend rm D:\data\file.zip
pylocalsend status
```

### 3. 在接收端下载

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

`download` 支持按文件名或文件 ID 下载。下载文件夹时会递归下载其中的文件。

## 接收端链接

发送端可以创建接收端记录，并生成带 token 的访问链接：

```powershell
pylocalsend receiver new --name laptop --pin 123456
pylocalsend receiver ls
pylocalsend receiver rm --id <receiver-id>
```

在 `pylocalsend gui` 中也可以管理接收端链接。通过链接访问时，Web 页面会列出可下载文件，并允许选择下载目录后开始下载。

## 配置

配置文件保存在用户目录下的 `.pylocalsend` 文件夹中。当前支持的配置项包括：

- `host`
- `port`
- `chunk_size`
- `max_parallel`
- `encryption_enabled`
- `pin_verification_enabled`
- `server_pin`

查看和修改配置：

```powershell
pylocalsend config-show
pylocalsend config-show --key port
pylocalsend config-set --key port 8765
pylocalsend config-set --key encryption_enabled true
```

## 当前已实现功能

- 发送端 CLI 服务和发送端 WebUI
- 本地文件、文件夹路径注册和删除
- 远程文件列表查询
- 文件和文件夹递归下载
- HTTP Range 断点续传
- 可选 AES-CTR 传输加密
- PIN 验证和接收端 token 链接
- 多文件并行下载和命令行进度条
- 下载记录、接收端记录和基础配置持久化

## 测试

```powershell
pytest tests -v
```
