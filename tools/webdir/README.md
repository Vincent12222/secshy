# WebDir 目录扫描独立版

这是从 TscanPlus 中“目录扫描模块”剥离出来的一个 **完全独立** 小项目：

- 使用自己的 `config.yaml` / `FingerDir.yaml`
- 不再依赖原 TscanPlus 目录结构或其 `config/config.yaml`
- 带简单 GUI，可视化查看扫描结果

## 目录结构

- `scanner.py`：核心目录扫描逻辑
- `gui.py`：Tkinter GUI 界面（入口）
- `config.yaml`：扫描参数配置（线程数、过滤规则等）
- `FingerDir.yaml`：常见组件的目录指纹
- `requirements.txt`：Python 依赖

## 部署为单独项目

1. 将整个 `webdir` 目录拷贝到 D 盘，例如：`D:\webdir`
2. 安装依赖：

```bash
cd D:\webdir
pip install -r requirements.txt
```

3. 启动 GUI：

```bash
python gui.py
```

> 只要 `D:\webdir` 这个目录是完整的，就可以在任何机器上独立运行，无需 TscanPlus。

## 使用说明（GUI）

- **目标 URL**：填写要扫描的网站，如 `https://example.com` 或 `example.com`
- **配置文件**：默认使用当前目录下的 `config.yaml`，也可以手动选择其他 YAML
- **指纹文件**：默认使用当前目录下的 `FingerDir.yaml`
- **字典文件**：可选，文本文件，每行一个路径（如 `/admin/`）。**如果留空，则自动加载当前目录下 `DirDict` 里的所有内置字典**；若 `DirDict` 也不存在，则退回到少量内置常见路径。
- **线程数(可选)**：指定后覆盖 `config.yaml` 里的 `DirThreadStr`
- **忽略 HTTPS 证书校验**：勾选后可以忽略 HTTPS 证书错误

点击 **“开始扫描”**：

- 下方文本框实时输出：`状态码 URL [目录枚举点 指纹:组件名...]`

点击 **“停止”**：

- 发送停止信号，等待当前任务安全结束。

