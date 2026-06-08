---
marp: true
theme: default
paginate: true
size: 16:9
title: PyLocalSend 课程展示
description: 局域网文件传输工具 PyLocalSend 的课堂展示课件
---

<style>
:root {
  --ink: #0f172a;
  --muted: #64748b;
  --line: rgba(148, 163, 184, 0.28);
  --blue: #2563eb;
  --cyan: #06b6d4;
  --green: #10b981;
  --violet: #7c3aed;
  --paper: #f8fafc;
  --card: rgba(255, 255, 255, 0.82);
}

section {
  width: 1280px;
  height: 720px;
  padding: 54px 66px;
  background:
    radial-gradient(circle at 10% 5%, rgba(37, 99, 235, 0.16), transparent 34%),
    radial-gradient(circle at 88% 16%, rgba(6, 182, 212, 0.15), transparent 30%),
    linear-gradient(135deg, #f8fafc 0%, #eef2ff 52%, #ecfeff 100%);
  color: var(--ink);
  font-family: "Microsoft YaHei", "Segoe UI", "PingFang SC", sans-serif;
  letter-spacing: 0.01em;
}

section::after {
  color: #94a3b8;
  font-size: 18px;
  right: 44px;
  bottom: 24px;
}

h1, h2, h3, p {
  margin: 0;
}

h1 {
  font-size: 70px;
  line-height: 1.02;
  letter-spacing: -0.05em;
}

h2 {
  margin-bottom: 28px;
  font-size: 44px;
  line-height: 1.12;
  letter-spacing: -0.03em;
}

h3 {
  margin-bottom: 10px;
  font-size: 24px;
}

p, li {
  font-size: 24px;
  line-height: 1.55;
}

ul, ol {
  margin: 0;
  padding-left: 1.25em;
}

li + li {
  margin-top: 10px;
}

strong {
  color: var(--blue);
}

code {
  padding: 0.08em 0.35em;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-family: "Cascadia Code", "JetBrains Mono", Consolas, monospace;
}

pre {
  margin: 0;
  padding: 24px 26px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 22px;
  background: #0f172a;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.20);
}

pre code {
  padding: 0;
  background: transparent;
  color: #e2e8f0;
  font-size: 21px;
  line-height: 1.5;
}

.eyebrow {
  margin-bottom: 14px;
  color: var(--blue);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.subtitle {
  margin-top: 20px;
  max-width: 780px;
  color: var(--muted);
  font-size: 27px;
  line-height: 1.5;
}

.caption {
  color: var(--muted);
  font-size: 18px;
}

.accent {
  display: inline-block;
  background: linear-gradient(90deg, var(--blue), var(--cyan));
  -webkit-background-clip: text;
  color: transparent;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 34px;
}

.chip {
  padding: 9px 15px;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #334155;
  font-size: 18px;
  font-weight: 700;
}

.grid {
  display: grid;
  gap: 18px;
}

.cols-2 {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.cols-3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.card {
  padding: 26px;
  border: 1px solid var(--line);
  border-radius: 26px;
  background: var(--card);
  box-shadow: 0 20px 55px rgba(15, 23, 42, 0.10);
}

.card p, .card li {
  color: #475569;
  font-size: 20px;
}

.metric {
  padding: 24px;
  border-radius: 26px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.94), rgba(6, 182, 212, 0.90));
  color: white;
  box-shadow: 0 24px 65px rgba(37, 99, 235, 0.22);
}

.metric b {
  display: block;
  margin-bottom: 8px;
  font-size: 42px;
  line-height: 1;
}

.metric span {
  font-size: 18px;
  opacity: 0.88;
}

.split {
  display: grid;
  grid-template-columns: 0.95fr 1.05fr;
  gap: 34px;
  align-items: center;
}

.terminal {
  position: relative;
  overflow: hidden;
}

.terminal::before {
  content: "";
  display: block;
  width: 42px;
  height: 10px;
  margin-bottom: 18px;
  border-radius: 999px;
  background: linear-gradient(90deg, #ef4444 0 9px, transparent 9px 16px, #f59e0b 16px 25px, transparent 25px 32px, #22c55e 32px 42px);
}

.flow {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  align-items: stretch;
}

.step {
  position: relative;
  min-height: 142px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.78);
}

.step b {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  border-radius: 50%;
  background: var(--ink);
  color: white;
  font-size: 18px;
}

.step span {
  display: block;
  color: #475569;
  font-size: 18px;
  line-height: 1.35;
}

.arch {
  display: grid;
  grid-template-columns: 1fr 0.55fr 1fr;
  gap: 22px;
  align-items: center;
  margin-top: 10px;
}

.machine {
  min-height: 330px;
  padding: 26px;
  border: 1px solid var(--line);
  border-radius: 30px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.10);
}

.machine h3 {
  color: var(--blue);
}

.node {
  margin-top: 13px;
  padding: 13px 15px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.05);
  color: #334155;
  font-size: 19px;
}

.wire {
  display: flex;
  min-height: 190px;
  align-items: center;
  justify-content: center;
  border-radius: 30px;
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.12), rgba(6, 182, 212, 0.12));
  color: var(--blue);
  font-size: 22px;
  font-weight: 800;
  text-align: center;
}

.timeline {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.timeline .card {
  min-height: 210px;
}

.badge {
  display: inline-block;
  margin-bottom: 18px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.10);
  color: var(--blue);
  font-size: 16px;
  font-weight: 800;
}

.quote {
  padding: 34px 40px;
  border-left: 7px solid var(--blue);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.10);
}

.quote p {
  font-size: 34px;
  line-height: 1.45;
  letter-spacing: -0.02em;
}

section.cover {
  padding: 74px 78px;
  background:
    radial-gradient(circle at 78% 23%, rgba(34, 211, 238, 0.34), transparent 27%),
    radial-gradient(circle at 18% 18%, rgba(96, 165, 250, 0.30), transparent 30%),
    linear-gradient(135deg, #020617 0%, #0f172a 50%, #083344 100%);
  color: white;
}

section.cover::after,
section.divider::after {
  color: rgba(255, 255, 255, 0.55);
}

section.cover h1 {
  max-width: 760px;
  font-size: 82px;
}

section.cover .subtitle,
section.cover .caption {
  color: rgba(226, 232, 240, 0.86);
}

section.cover .chip {
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.10);
  color: #e2e8f0;
}

section.divider {
  display: flex;
  flex-direction: column;
  justify-content: center;
  background:
    radial-gradient(circle at 78% 20%, rgba(34, 211, 238, 0.32), transparent 28%),
    linear-gradient(135deg, #111827 0%, #1e3a8a 62%, #0e7490 100%);
  color: white;
}

section.divider h1 {
  max-width: 900px;
  font-size: 64px;
}

section.divider .eyebrow,
section.divider .subtitle {
  color: rgba(226, 232, 240, 0.84);
}

section.closing {
  display: flex;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  background:
    radial-gradient(circle at 50% 20%, rgba(37, 99, 235, 0.22), transparent 30%),
    linear-gradient(135deg, #f8fafc, #e0f2fe);
}

section.closing h1 {
  font-size: 78px;
}
</style>

<!-- _class: cover -->

<div class="eyebrow">LAN File Transfer / Course Demo</div>

# PyLocalSend

<div class="subtitle">一个面向局域网的文件传输工具：发送端登记路径，接收端通过 CLI 或浏览器流式下载。</div>

<div class="chips">
  <span class="chip">Python</span>
  <span class="chip">FastAPI</span>
  <span class="chip">NiceGUI</span>
  <span class="chip">Streaming</span>
  <span class="chip">Zero-copy metadata</span>
</div>

<div style="position:absolute; right:78px; bottom:58px;" class="caption">课堂展示版 · PyLocalSend</div>

---

<!-- _class: divider -->

<div class="eyebrow">01 / Problem</div>

# 为什么需要一个局域网文件传输工具？

<div class="subtitle">课堂、宿舍、实验室里，文件共享最常见的问题不是“能不能传”，而是“能不能快速、低成本、可控地传”。</div>

---

## 传统方式的痛点

<div class="grid cols-3">
  <div class="card">
    <h3>U 盘复制</h3>
    <p>速度受设备影响，反复插拔，文件夹同步容易遗漏。</p>
  </div>
  <div class="card">
    <h3>网盘上传</h3>
    <p>需要公网中转，速度不稳定，也会带来账号和隐私成本。</p>
  </div>
  <div class="card">
    <h3>聊天软件</h3>
    <p>大文件限制多，目录结构不友好，不适合作为课堂分发工具。</p>
  </div>
</div>

<div class="quote" style="margin-top:28px;">
  <p>PyLocalSend 的目标：在同一局域网内，让发送端简单共享，让接收端尽量零成本下载。</p>
</div>

---

## 项目定位

<div class="grid cols-3">
  <div class="metric">
    <b>0</b>
    <span>接收端 WebUI 不需要安装客户端</span>
  </div>
  <div class="metric">
    <b>1</b>
    <span>发送端启动一个本地 HTTP 服务</span>
  </div>
  <div class="metric">
    <b>N</b>
    <span>多个接收端可通过链接访问下载</span>
  </div>
</div>

<div class="grid cols-2" style="margin-top:24px;">
  <div class="card">
    <h3>适合场景</h3>
    <ul>
      <li>课堂资料分发</li>
      <li>实验室内网共享</li>
      <li>临时大文件传输</li>
    </ul>
  </div>
  <div class="card">
    <h3>核心原则</h3>
    <ul>
      <li>发送端不提前复制文件</li>
      <li>下载时分片读取和流式返回</li>
      <li>CLI 和浏览器覆盖不同使用习惯</li>
    </ul>
  </div>
</div>

---

<!-- _class: divider -->

<div class="eyebrow">02 / Product</div>

# 用户看到的 PyLocalSend

<div class="subtitle">发送端负责管理，接收端负责下载。命令行适合精确控制，WebUI 适合课堂快速演示。</div>

---

## 两种入口

<div class="split">
  <div>
    <div class="eyebrow">Sender</div>
    <h2>发送端管理共享资源</h2>
    <ul>
      <li>启动服务并展示局域网地址</li>
      <li>注册文件或文件夹绝对路径</li>
      <li>创建接收端专属链接</li>
      <li>查看下载记录与配置</li>
    </ul>
  </div>
  <div class="grid cols-2">
    <div class="card">
      <h3>CLI</h3>
      <p>适合脚本化、批量下载、指定目标目录和断点续传。</p>
    </div>
    <div class="card">
      <h3>WebUI</h3>
      <p>适合课堂演示，接收端打开链接即可下载。</p>
    </div>
    <div class="card">
      <h3>PIN</h3>
      <p>基础身份验证，避免局域网内随意访问。</p>
    </div>
    <div class="card">
      <h3>Token</h3>
      <p>为每个接收端生成独立链接，便于管理和追踪。</p>
    </div>
  </div>
</div>

---

## 快速演示命令

<div class="split">
  <div>
    <h2>从启动到下载</h2>
    <p class="subtitle">发送端启动服务、登记路径；接收端通过地址和 PIN 获取列表并下载。</p>
    <div class="chips">
      <span class="chip">sender</span>
      <span class="chip">upload</span>
      <span class="chip">ls-remote</span>
      <span class="chip">download</span>
    </div>
  </div>
  <div class="terminal">
<pre><code>pylocalsend gui

pylocalsend upload D:\data\file.zip D:\photos

pylocalsend ls-remote `
  -H http://192.168.1.100:8765 --pin 123456

pylocalsend download file.zip `
  -d D:\downloads `
  -H http://192.168.1.100:8765 --pin 123456</code></pre>
  </div>
</div>

---

## 接收端 WebUI 的正确下载模型

<div class="grid cols-2">
  <div class="card">
    <span class="badge">Before</span>
    <h3>错误直觉</h3>
    <p>在 WebUI 输入下载目录，然后由 NiceGUI 回调写文件。</p>
    <p style="margin-top:14px;">问题：回调运行在发送端 Python 进程，路径会指向发送端电脑。</p>
  </div>
  <div class="card">
    <span class="badge">Now</span>
    <h3>当前方案</h3>
    <p>浏览器直接请求下载接口，由接收端浏览器保存文件。</p>
    <p style="margin-top:14px;">文件夹由发送端流式打包为 ZIP，浏览器保存为压缩包。</p>
  </div>
</div>

<div class="quote" style="margin-top:26px;">
  <p>WebUI 下载位置由接收端浏览器控制；如需每次选择位置，开启浏览器“下载前询问保存位置”。</p>
</div>

---

<!-- _class: divider -->

<div class="eyebrow">03 / Architecture</div>

# 系统架构与核心流程

<div class="subtitle">核心思想是“路径登记 + 按需读取 + 流式返回”。</div>

---

## 整体架构

<div class="arch">
  <div class="machine">
    <h3>发送端电脑</h3>
    <div class="node">SenderService / FastAPI</div>
    <div class="node">NiceGUI 发送端管理页</div>
    <div class="node">SQLite 元数据与下载日志</div>
    <div class="node">真实文件 / 文件夹</div>
  </div>

  <div class="wire">
    HTTP Stream<br>
    PIN / Token<br>
    Range
  </div>

  <div class="machine">
    <h3>接收端电脑</h3>
    <div class="node">CLI ReceiverClient</div>
    <div class="node">浏览器 Receiver WebUI</div>
    <div class="node">本地下载目录</div>
    <div class="node">浏览器下载管理器</div>
  </div>
</div>

---

## 文件共享流程

<div class="flow">
  <div class="step"><b>1</b><span>启动发送端服务或 WebUI</span></div>
  <div class="step"><b>2</b><span>登记本地文件/文件夹路径</span></div>
  <div class="step"><b>3</b><span>保存元数据到 SQLite</span></div>
  <div class="step"><b>4</b><span>接收端获取文件列表</span></div>
  <div class="step"><b>5</b><span>发起下载请求</span></div>
  <div class="step"><b>6</b><span>发送端流式读取并返回</span></div>
</div>

<div class="grid cols-3" style="margin-top:30px;">
  <div class="card"><h3>不复制</h3><p>注册时只记录路径和元数据。</p></div>
  <div class="card"><h3>不缓存</h3><p>下载时直接读取源文件。</p></div>
  <div class="card"><h3>不阻塞内存</h3><p>分片读写，适合大文件。</p></div>
</div>

---

## 文件夹下载策略

<div class="grid cols-2">
  <div class="card">
    <span class="badge">CLI</span>
    <h3>递归下载</h3>
    <ul>
      <li>先获取目录树</li>
      <li>按相对路径创建本地文件</li>
      <li>支持并行和断点续传</li>
    </ul>
  </div>
  <div class="card">
    <span class="badge">Browser WebUI</span>
    <h3>ZIP 流下载</h3>
    <ul>
      <li>按需枚举文件夹</li>
      <li>边读取边写入 ZIP 响应</li>
      <li>不在发送端生成临时压缩包</li>
    </ul>
  </div>
</div>

<div class="terminal" style="margin-top:28px;">
<pre><code>folder/                 browser download
  a.txt      ───────▶   folder.zip
  nested/
    b.txt</code></pre>
</div>

---

## 安全与可追踪

<div class="timeline">
  <div class="card">
    <span class="badge">Auth</span>
    <h3>PIN 验证</h3>
    <p>发送端统一 PIN，用于 CLI 和 API 请求。</p>
  </div>
  <div class="card">
    <span class="badge">Link</span>
    <h3>接收端 Token</h3>
    <p>为具体接收端生成专属访问链接。</p>
  </div>
  <div class="card">
    <span class="badge">Crypto</span>
    <h3>AES-CTR</h3>
    <p>CLI 路径支持可选加密流和解密。</p>
  </div>
  <div class="card">
    <span class="badge">Log</span>
    <h3>下载记录</h3>
    <p>记录接收者、时间、状态和字节数。</p>
  </div>
</div>

---

<!-- _class: divider -->

<div class="eyebrow">04 / Implementation</div>

# 技术实现拆解

<div class="subtitle">项目边界清晰：CLI、GUI、Core 分层，业务逻辑集中在 core 中复用。</div>

---

## 技术栈

<div class="grid cols-3">
  <div class="card"><h3>FastAPI</h3><p>HTTP API、鉴权、文件下载流。</p></div>
  <div class="card"><h3>NiceGUI</h3><p>发送端管理页和接收端 WebUI。</p></div>
  <div class="card"><h3>httpx</h3><p>CLI 接收端请求文件列表和下载流。</p></div>
  <div class="card"><h3>Rich</h3><p>命令行多文件下载进度条。</p></div>
  <div class="card"><h3>SQLite</h3><p>共享文件、接收端和日志持久化。</p></div>
  <div class="card"><h3>cryptography</h3><p>AES-CTR 可寻址加密流。</p></div>
</div>

---

## 项目结构

<div class="split">
  <div>
    <h2>Core 负责业务能力</h2>
    <p class="subtitle">GUI 和 CLI 不重复实现传输逻辑，而是复用 core 层能力。</p>
  </div>
  <div class="terminal">
<pre><code>pylocalsend/
  cli/                 # 命令行入口
  core/
    file_handler/      # 元数据、目录遍历、分片读写
    receiver/          # 接收端下载客户端
    transfer/          # 发送端服务和 API
    utils/             # 配置、数据库、加密、网络
  gui/
    sender/            # 发送端 WebUI
    receiver/          # 接收端 WebUI
tests/
doc/</code></pre>
  </div>
</div>

---

## 数据持久化

<div class="split">
  <div class="terminal">
<pre><code>~/.pylocalsend/
  config.json
  session.json
  pylocalsend.db</code></pre>
  </div>
  <div>
    <h2>保存什么？</h2>
    <ul>
      <li>共享文件路径、大小、时间、状态</li>
      <li>接收端名称、PIN、token、状态</li>
      <li>下载记录、开始/结束时间、传输字节数</li>
      <li>端口、分片大小、并行数、加密开关</li>
    </ul>
  </div>
</div>

---

## 测试重点

<div class="grid cols-2">
  <div class="card">
    <h3>命令行行为</h3>
    <p>参数解析、连接保存、下载调用、配置读取。</p>
  </div>
  <div class="card">
    <h3>发送端服务</h3>
    <p>文件注册、下载接口、鉴权和日志记录。</p>
  </div>
  <div class="card">
    <h3>浏览器下载</h3>
    <p>query token 鉴权，浏览器路径返回明文流。</p>
  </div>
  <div class="card">
    <h3>文件夹 ZIP</h3>
    <p>目录内容被流式打包，浏览器获取 ZIP。</p>
  </div>
</div>

<div class="terminal" style="margin-top:24px;">
<pre><code>pip install -e ".[dev]"
pytest tests -v</code></pre>
</div>

---

<!-- _class: divider -->

<div class="eyebrow">05 / Demo Plan</div>

# 课堂演示安排

<div class="subtitle">按“发送端管理 - 接收端访问 - 下载记录验证”的顺序展示，逻辑最清楚。</div>

---

## 演示脚本

<div class="timeline">
  <div class="card">
    <span class="badge">Step 1</span>
    <h3>启动 WebUI</h3>
    <p>运行 `pylocalsend gui`，展示发送端地址。</p>
  </div>
  <div class="card">
    <span class="badge">Step 2</span>
    <h3>注册资源</h3>
    <p>添加一个单文件和一个文件夹。</p>
  </div>
  <div class="card">
    <span class="badge">Step 3</span>
    <h3>创建链接</h3>
    <p>为接收端生成 token 链接并复制。</p>
  </div>
  <div class="card">
    <span class="badge">Step 4</span>
    <h3>接收下载</h3>
    <p>浏览器下载单文件和文件夹 ZIP。</p>
  </div>
</div>

<div class="quote" style="margin-top:26px;">
  <p>最后回到发送端查看下载记录，证明接收者、状态和传输记录已经持久化。</p>
</div>

---

## 当前限制与改进方向

<div class="grid cols-2">
  <div class="card">
    <h3>当前限制</h3>
    <ul>
      <li>WebUI 保存位置由浏览器控制</li>
      <li>公网访问需要额外端口映射</li>
      <li>局域网 HTTP 默认不是 HTTPS</li>
    </ul>
  </div>
  <div class="card">
    <h3>后续可做</h3>
    <ul>
      <li>二维码分享接收端链接</li>
      <li>更完整的下载任务状态面板</li>
      <li>接收端页面批量下载打包优化</li>
    </ul>
  </div>
</div>

---

<!-- _class: closing -->

<div class="eyebrow">Summary</div>

# PyLocalSend

<div class="subtitle" style="margin-left:auto; margin-right:auto;">发送端只登记路径，下载时流式读取；CLI 适合高级控制，WebUI 适合零安装接收。</div>

<div class="chips" style="justify-content:center;">
  <span class="chip">低成本</span>
  <span class="chip">局域网</span>
  <span class="chip">流式传输</span>
  <span class="chip">可管理</span>
</div>

---

<!-- _class: cover -->

# Q&A

<div class="subtitle">谢谢观看</div>

