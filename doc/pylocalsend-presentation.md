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
  --paper: #fbfaf7;
  --paper-soft: #f4f1eb;
  --ink: #1f1f1d;
  --muted: #77736a;
  --faint: #d9d4ca;
  --hairline: #e7e2d8;
  --accent: #b33a2e;
}

section {
  width: 1280px;
  height: 720px;
  padding: 72px 92px;
  background: var(--paper);
  color: var(--ink);
  font-family: "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
  letter-spacing: 0.02em;
}

section::before {
  content: "";
  position: absolute;
  left: 92px;
  top: 44px;
  width: calc(100% - 184px);
  height: 1px;
  background: var(--hairline);
}

section::after {
  right: 92px;
  bottom: 42px;
  color: #aaa399;
  font-size: 14px;
}

h1, h2, h3, p {
  margin: 0;
}

h1 {
  max-width: 780px;
  font-size: 64px;
  font-weight: 300;
  line-height: 1.16;
  letter-spacing: 0.04em;
}

h2 {
  max-width: 760px;
  margin-bottom: 42px;
  font-size: 42px;
  font-weight: 300;
  line-height: 1.24;
  letter-spacing: 0.04em;
}

h3 {
  margin-bottom: 12px;
  font-size: 22px;
  font-weight: 400;
  letter-spacing: 0.06em;
}

p, li {
  color: var(--muted);
  font-size: 22px;
  font-weight: 300;
  line-height: 1.72;
}

ul, ol {
  margin: 0;
  padding-left: 1.15em;
}

li + li {
  margin-top: 8px;
}

strong {
  color: var(--ink);
  font-weight: 500;
}

code {
  padding: 0.08em 0.28em;
  border: 1px solid var(--hairline);
  border-radius: 0;
  background: rgba(255, 255, 255, 0.42);
  color: var(--ink);
  font-family: "Cascadia Code", "JetBrains Mono", Consolas, monospace;
  font-size: 0.9em;
}

pre {
  margin: 0;
  padding: 28px 30px;
  border: 1px solid var(--hairline);
  background: rgba(255, 255, 255, 0.46);
}

pre code {
  padding: 0;
  border: none;
  background: transparent;
  color: #3f3c37;
  font-size: 19px;
  line-height: 1.65;
}

.kicker {
  margin-bottom: 30px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.26em;
  text-transform: uppercase;
}

.sub {
  max-width: 680px;
  margin-top: 26px;
  color: var(--muted);
  font-size: 24px;
  font-weight: 300;
  line-height: 1.7;
}

.small {
  color: #9b958b;
  font-size: 15px;
  letter-spacing: 0.08em;
}

.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 14px;
  border-radius: 50%;
  background: var(--accent);
  vertical-align: middle;
}

.columns {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 72px;
  align-items: start;
}

.columns.three {
  grid-template-columns: repeat(3, 1fr);
  gap: 36px;
}

.panel {
  min-height: 176px;
  padding: 24px 0 0;
  border-top: 1px solid var(--faint);
}

.panel p,
.panel li {
  font-size: 19px;
  line-height: 1.66;
}

.number {
  display: block;
  margin-bottom: 22px;
  color: var(--accent);
  font-size: 42px;
  font-weight: 200;
  line-height: 1;
}

.split {
  display: grid;
  grid-template-columns: 0.88fr 1.12fr;
  gap: 76px;
  align-items: center;
}

.wide {
  max-width: 900px;
}

.quote {
  max-width: 900px;
  padding-left: 34px;
  border-left: 1px solid var(--accent);
}

.quote p {
  color: var(--ink);
  font-size: 34px;
  font-weight: 300;
  line-height: 1.55;
  letter-spacing: 0.04em;
}

.line-list {
  border-top: 1px solid var(--faint);
}

.line-item {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 26px;
  padding: 18px 0;
  border-bottom: 1px solid var(--hairline);
}

.line-item b {
  color: var(--ink);
  font-size: 18px;
  font-weight: 400;
}

.line-item span {
  color: var(--muted);
  font-size: 19px;
  line-height: 1.55;
}

.flow {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0;
  border-top: 1px solid var(--faint);
  border-left: 1px solid var(--faint);
}

.step {
  min-height: 190px;
  padding: 24px 18px;
  border-right: 1px solid var(--faint);
  border-bottom: 1px solid var(--faint);
}

.step b {
  display: block;
  margin-bottom: 36px;
  color: var(--accent);
  font-size: 18px;
  font-weight: 400;
}

.step span {
  color: var(--muted);
  font-size: 18px;
  line-height: 1.55;
}

.arch {
  display: grid;
  grid-template-columns: 1fr 210px 1fr;
  gap: 0;
  align-items: stretch;
  border: 1px solid var(--faint);
}

.machine {
  padding: 34px;
  background: rgba(255, 255, 255, 0.24);
}

.machine + .wire,
.wire + .machine {
  border-left: 1px solid var(--faint);
}

.node {
  padding: 14px 0;
  border-bottom: 1px solid var(--hairline);
  color: var(--muted);
  font-size: 18px;
}

.wire {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: var(--accent);
  font-size: 17px;
  font-weight: 400;
  line-height: 1.9;
  text-align: center;
  letter-spacing: 0.08em;
}

.label-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 34px;
}

.label {
  padding: 7px 12px;
  border: 1px solid var(--hairline);
  color: var(--muted);
  font-size: 14px;
  letter-spacing: 0.08em;
}

section.cover,
section.chapter,
section.end {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

section.cover::before,
section.chapter::before,
section.end::before {
  background: transparent;
}

section.cover {
  padding: 88px 104px;
}

section.cover h1 {
  font-size: 78px;
  letter-spacing: 0.08em;
}

section.cover .mark {
  position: absolute;
  right: 112px;
  top: 92px;
  width: 72px;
  height: 72px;
  border: 1px solid var(--accent);
  border-radius: 50%;
}

section.cover .mark::after {
  content: "";
  position: absolute;
  left: 31px;
  top: 31px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
}

section.chapter {
  background: var(--paper-soft);
}

section.chapter h1 {
  max-width: 940px;
  font-size: 56px;
}

section.chapter .chapter-no {
  margin-bottom: 42px;
  color: var(--accent);
  font-size: 15px;
  letter-spacing: 0.26em;
}

section.end {
  text-align: center;
}

section.end h1,
section.end .sub {
  margin-left: auto;
  margin-right: auto;
}

section.end .label-row {
  width: 100%;
  justify-content: center;
  margin-left: auto;
  margin-right: auto;
}
</style>

<!-- _class: cover -->

<div class="mark"></div>

<div class="kicker">LAN FILE TRANSFER / COURSE DEMO</div>

# PyLocalSend

<div class="sub">一个面向局域网的文件传输工具。发送端登记路径，接收端通过 CLI 或浏览器下载；也可按需允许接收端反向上传。</div>

<div style="position:absolute; left:104px; bottom:76px;" class="small">Python · FastAPI · NiceGUI · Streaming</div>

---

<!-- _class: chapter -->

<div class="chapter-no">01 / PROBLEM</div>

# 文件传输的问题，常常不在“能不能传”

<div class="sub">而在于能不能低成本、少步骤、稳定地把文件送到接收端。</div>

---

## 传统方式的阻力

<div class="columns three">
  <div class="panel">
    <span class="number">01</span>
    <h3>U 盘</h3>
    <p>依赖设备，反复插拔，文件夹内容容易遗漏。</p>
  </div>
  <div class="panel">
    <span class="number">02</span>
    <h3>网盘</h3>
    <p>需要公网中转，速度和隐私都不完全可控。</p>
  </div>
  <div class="panel">
    <span class="number">03</span>
    <h3>聊天软件</h3>
    <p>大文件限制多，目录结构不友好。</p>
  </div>
</div>

<div class="quote" style="margin-top:64px;">
  <p>PyLocalSend 试图把“传文件”变简单。</p>
</div>

---

## &#20256;&#32479;&#26041;&#26696;&#65306;&#20808;&#22797;&#21046;&#21040;&#20869;&#23384;

<img src="./%E4%BC%A0%E7%BB%9F%E6%96%B9%E6%A1%88.svg" style="display:block; width:1040px; margin:24px auto 0;" alt="传统方案文件传输流程">

---

## PyLocalSend &#26041;&#26696;&#65306;&#36793;&#35835;&#36793;&#21457;

<img src="./pylocalsend-stream.svg" style="display:block; width:1040px; margin:24px auto 0;" alt="PyLocalSend 流式文件传输流程">

---

## 项目定位

<div class="columns">
  <div>
    <h2>发送端负责共享，接收端负责下载。</h2>
    <p class="sub">不引入复杂账号系统，不依赖公网服务，不提前复制文件。</p>
  </div>
  <div class="line-list">
    <div class="line-item"><b>接收端零安装</b><span>WebUI 打开链接即可下载。</span></div>
    <div class="line-item"><b>1 服务</b><span>发送端启动本地 HTTP 服务。</span></div>
    <div class="line-item"><b>N 接收</b><span>多个接收端通过 PIN 或 token 访问。</span></div>
  </div>
</div>

---

<!-- _class: chapter -->

<div class="chapter-no">02 / PRODUCT</div>

# 两种使用方式

<div class="sub">CLI 负责精确控制，WebUI 负责轻量接收。</div>

---

## 发送端 WebUI

<div class="split">
  <div>
    <h2>只管理共享路径，不复制文件。</h2>
    <p class="sub">发送端只登记本地文件或文件夹路径，界面负责展示和管理。</p>
  </div>
  <div class="line-list">
    <div class="line-item"><b>文件</b><span>注册、查看、删除共享路径；勾选控制开放范围。</span></div>
    <div class="line-item"><b>接收端</b><span>创建 token 链接；允许/禁止浏览器上传；禁用/启用。</span></div>
    <div class="line-item"><b>记录</b><span>查看下载者、时间、状态和传输量。</span></div>
    <div class="line-item"><b>设置</b><span>分片大小、浏览器上传存放路径；亦可改端口、PIN、加密等。</span></div>
  </div>
</div>

---

## CLI 使用

<div class="split">
  <div>
    <h2>适合批量和精确下载。</h2>
    <p class="sub">命令行可指定目标目录，支持并行下载和断点续传。</p>
    <div class="label-row">
      <span class="label">sender</span>
      <span class="label">upload</span>
      <span class="label">ls-remote</span>
      <span class="label">download</span>
    </div>
  </div>
  <div>
<pre><code>pylocalsend gui

pylocalsend upload D:\data\file.zip D:\photos

pylocalsend ls-remote `
-H http://192.168.1.100:8765 --pin 123456

pylocalsend download file.zip `  -d D:\downloads`
-H http://192.168.1.100:8765 --pin 123456</code></pre>

  </div>
</div>

---

## 接收端 WebUI

<div class="columns">
  <div class="panel">
    <span class="number">A</span>
    <h3>单文件</h3>
    <p>浏览器直接请求下载接口，文件保存到接收端浏览器下载目录。</p>
  </div>
  <div class="panel">
    <span class="number">B</span>
    <h3>文件夹</h3>
    <p>发送端按开放范围生成 ZIP 流，浏览器保存为 `<文件夹名>.zip`。</p>
  </div>
</div>

<div class="quote" style="margin-top:72px;">
  <p>仅显示发送端已勾选的项；catalog 版本轮询自动同步，无需手动刷新。</p>
</div>

---

## 接收端浏览器上传

<div class="columns">
  <div class="panel">
    <span class="number">C</span>
    <h3>权限开关</h3>
    <p>发送端在「接收端管理」中按接收端单独<strong>允许上传</strong>或<strong>禁止上传</strong>；默认禁止。</p>
  </div>
  <div class="panel">
    <span class="number">D</span>
    <h3>上传标签页</h3>
    <p>被允许的接收端打开 `/r/&lt;token&gt;` 后，页面出现<strong>「上传文件」</strong>标签，使用 NiceGUI 上传组件，支持多文件自动上传。</p>
  </div>
</div>

<div class="columns three" style="margin-top:36px;">
  <div class="panel"><h3>存放路径</h3><p><code>{upload_dir}/{接收端名称}/</code>；<code>upload_dir</code> 可在设置中配置。</p></div>
  <div class="panel"><h3>默认目录</h3><p>留空时使用 <code>~/.pylocalsend/browser_uploads</code>。</p></div>
  <div class="panel"><h3>同名处理</h3><p>目标文件已存在时自动追加时间戳，避免覆盖。</p></div>
</div>

---

## 下载开放与接收端控制

<div class="columns">
  <div class="panel">
    <span class="number">01</span>
    <h3>开放勾选</h3>
    <p>发送端首列复选框决定对接收端可见的路径；子文件夹/子文件支持级联选择，状态写入 `download_grants`。</p>
  </div>
  <div class="panel">
    <span class="number">02</span>
    <h3>禁用接收端</h3>
    <p>禁用后禁止新下载、新上传，并中断进行中的下载；解除禁用后 token 链接恢复正常。</p>
  </div>
</div>

<div class="columns three" style="margin-top:36px;">
  <div class="panel"><h3>允许上传</h3><p>按接收端开启浏览器反向传文件到发送端电脑。</p></div>
  <div class="panel"><h3>全部开放</h3><p>一键开放所有已注册项。</p></div>
  <div class="panel"><h3>自动同步</h3><p>接收端每 2 秒检测 catalog-version 变化。</p></div>
</div>

---

<!-- _class: chapter -->

<div class="chapter-no">03 / ARCHITECTURE</div>

# 路径登记，按需读取，流式返回

<div class="sub">从“两次上传”变成“一次上传”</div>

---

## 整体架构

<div class="arch">
  <div class="machine">
    <h3>发送端电脑</h3>
    <div class="node">SenderService / FastAPI</div>
    <div class="node">NiceGUI 发送端管理页</div>
    <div class="node">SQLite 元数据与下载日志</div>
    <div class="node">本地真实文件 / 文件夹</div>
  </div>

  <div class="wire">
    HTTP<br>
    STREAM<br>
    PIN / TOKEN<br>
    RANGE<br>
    UPLOAD*
  </div>

  <div class="machine">
    <h3>接收端电脑</h3>
    <div class="node">CLI ReceiverClient</div>
    <div class="node">浏览器 Receiver WebUI</div>
    <div class="node">浏览器下载管理器</div>
    <div class="node">本地下载目录</div>
  </div>
</div>

---

## 文件共享流程

<div class="flow">
  <div class="step"><b>01</b><span>启动发送端服务</span></div>
  <div class="step"><b>02</b><span>登记文件或文件夹路径</span></div>
  <div class="step"><b>03</b><span>保存元数据到 SQLite</span></div>
  <div class="step"><b>04</b><span>接收端获取已开放文件列表</span></div>
  <div class="step"><b>05</b><span>发起下载请求</span></div>
  <div class="step"><b>06</b><span>发送端分片读取并返回</span></div>
</div>

<div class="columns three" style="margin-top:52px;">
  <div class="panel"><h3>不复制</h3><p>注册时只保存路径和元数据。</p></div>
  <div class="panel"><h3>不缓存</h3><p>下载时直接读取源文件。</p></div>
  <div class="panel"><h3>低内存占用</h3><p>分片读写，避免一次性加载大文件。</p></div>
</div>

---

## 文件夹下载策略

<div class="columns">
  <div class="panel">
    <span class="number">CLI</span>
    <h3>递归下载</h3>
    <ul>
      <li>获取目录树</li>
      <li>在接收端重建相对路径</li>
      <li>支持并行和断点续传</li>
    </ul>
  </div>
  <div class="panel">
    <span class="number">WEB</span>
    <h3>ZIP 流</h3>
    <ul>
      <li>按需枚举文件夹</li>
      <li>边读取边写入 ZIP 响应</li>
      <li>不生成临时压缩包</li>
    </ul>
  </div>
</div>

<div style="margin-top:46px;">
<pre><code>folder/                 browser download
  a.txt      -------->  folder.zip
  nested/
    b.txt</code></pre>
</div>

---

## 访问控制与记录

<div class="line-list">
  <div class="line-item"><b>PIN</b><span>发送端统一 PIN，CLI 与 API 鉴权。</span></div>
  <div class="line-item"><b>TOKEN</b><span>每接收端独立链接；可禁用/启用，临时管控下载与上传。</span></div>
  <div class="line-item"><b>GRANT</b><span>按路径控制可见性；列表、树、下载、ZIP 均过滤。</span></div>
  <div class="line-item"><b>UPLOAD</b><span>按接收端开关浏览器上传；<code>upload_dir</code> 配置存放根目录。</span></div>
  <div class="line-item"><b>LOG</b><span>记录下载者、时间、状态与传输字节数。</span></div>
  <div class="line-item"><b>VER</b><span>共享项与 grants 哈希为 catalog 版本；WebUI 轮询自动同步。</span></div>
</div>

---

<!-- _class: chapter -->

<div class="chapter-no">04 / IMPLEMENTATION</div>

# 代码结构保持清晰

<div class="sub">CLI 和 GUI 只是入口，核心能力集中在 `core` 层。</div>

---

## 技术栈

<div class="line-list">
  <div class="line-item"><b>FastAPI</b><span>提供 HTTP API、鉴权、文件下载流。</span></div>
  <div class="line-item"><b>NiceGUI</b><span>构建发送端管理页面和接收端 WebUI。</span></div>
  <div class="line-item"><b>httpx</b><span>接收端 CLI 请求列表和下载流。</span></div>
  <div class="line-item"><b>Rich</b><span>命令行多文件下载进度条。</span></div>
  <div class="line-item"><b>SQLite</b><span>保存共享文件、接收端和下载记录。</span></div>
  <div class="line-item"><b>cryptography</b><span>AES-CTR 可寻址加密流。</span></div>
</div>

---

## 项目结构

<div class="split">
  <div>
    <h2>Core 提供业务能力。</h2>
    <p class="sub">不同入口复用同一套传输、配置、数据库和加密逻辑。</p>
  </div>
  <div>
<pre><code>pylocalsend/
  cli/                 # 命令行入口
  core/
    file_handler/      # 元数据、目录遍历、分片读写、download_grants
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
  <div>
<pre><code>~/.pylocalsend/
  config.json
  session.json
  pylocalsend.db</code></pre>
  </div>
  <div class="line-list">
    <div class="line-item"><b>files</b><span>路径、名称、大小、类型、状态。</span></div>
    <div class="line-item"><b>download_grants</b><span>每个共享项的开放相对路径。</span></div>
    <div class="line-item"><b>receivers</b><span>名称、PIN、token、状态、upload_allowed。</span></div>
    <div class="line-item"><b>config</b><span>含 upload_dir：浏览器上传存放根目录。</span></div>
    <div class="line-item"><b>logs</b><span>下载者、时间、状态、字节数。</span></div>
  </div>
</div>

---

<!-- _class: chapter -->

<div class="chapter-no">05 / DEMO</div>

# 课堂演示

---

## 演示视频

<video src="./video/demo.mp4" controls style="display:block; width:1040px; margin:24px auto 0; border:1px solid #e7e2d8; background:#fff;"></video>

---

## 当前限制

<div class="columns">
  <div class="panel">
    <h3>浏览器限制</h3>
    <p>WebUI 下载位置由浏览器控制，不能任意写入绝对路径。</p>
  </div>
  <div class="panel">
    <h3>网络边界</h3>
    <p>当前默认面向可信局域网；直接公网访问需要额外配置和安全加固。</p>
  </div>
</div>

<div class="columns" style="margin-top:36px;">
  <div class="panel">
    <h3>上传不自动共享</h3>
    <p>接收端上传后需发送端手动注册路径，才会出现在共享列表并开放下载。</p>
  </div>
  <div class="panel">
    <h3>接收端上传体积</h3>
    <p>WebUI 上传经浏览器读入内存再写入磁盘，超大文件更适合 CLI 或本机路径注册。</p>
  </div>
</div>

<div class="quote" style="margin-top:48px;">
  <p>CLI 更适合复杂批量下载；WebUI 更适合零安装接收、反向上传和课堂演示。</p>
</div>

---

<!-- _class: end -->

<div class="kicker">SUMMARY</div>

# PyLocalSend

<div class="sub">发送端只登记路径，下载时流式读取。尽量降低操作复杂度，让文件更直接地抵达接收端。</div>

<div class="label-row" style="margin-top:44px;">
  <span class="label">低成本</span>
  <span class="label">局域网</span>
  <span class="label">流式传输</span>
  <span class="label">可管理</span>
  <span class="label">细粒度开放</span>
  <span class="label">反向上传</span>
</div>

---

<div class="line-list" style="max-width:760px; margin:48px auto 0; text-align:left;">
  <div class="line-item"><b>李子健</b><span>GUI 和 CLI 设计和实现，核心逻辑代码，视频剪辑</span></div>
  <div class="line-item"><b>杨秉熹</b><span>核心逻辑代码，视频素材提供，PPT 制作</span></div>
</div>

---

<!-- _class: end -->

# Q&A

<div class="sub">谢谢观看</div>

