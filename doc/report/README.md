# PyLocalSend 报告编译说明

本目录用于在 Overleaf 编译项目技术报告。

## 上传文件

将以下内容上传到同一个 Overleaf 项目：

- `main.tex`
- `figures/` 目录及其中全部 `.svg` 图片

## 编译设置

在 Overleaf 左上角 Menu 中设置：

- Compiler: `XeLaTeX`
- Main document: `main.tex`

报告使用 `ctexart` 支持中文，使用 `svg` 宏包插入 SVG 图片。Overleaf 通常可以自动调用 Inkscape 转换 SVG。

如果 SVG 转换失败，可在本地或在线工具中将 `figures/*.svg` 转为 PDF，然后把 `main.tex` 中的 `\includesvg{figures/name}` 改为 `\includegraphics{figures/name.pdf}`，并将导言区的 `\usepackage{svg}` 改为 `\usepackage{graphicx}`。
