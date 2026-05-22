# SkillCode2Drawio

`SkillCode2Drawio` 是一个面向 Codex 的绘图技能集合，核心 skill 为 `code-drawio-direct`。它用于在分析项目代码逻辑后，直接生成可编辑的 diagrams.net / draw.io `.drawio` 文件，不依赖 Mermaid 作为中间格式。

## 主要能力

- 根据函数、模块、接口、任务流程等代码逻辑生成流程图。
- 使用简洁的 `.diagram.json` 描述图结构，再由脚本生成原生 `.drawio` XML。
- 支持多页图、分支节点、外部系统节点、数据存储节点、错误路径和重试/回环路径。
- 默认使用正交连线，便于后续在 draw.io 中继续编辑。
- 可选导出 PNG、SVG、PDF 等展示文件。

## 目录结构

```text
SkillCode2Drawio/
├─ README.md
└─ code-drawio-direct/
   ├─ SKILL.md
   ├─ agents/
   ├─ examples/
   ├─ references/
   └─ scripts/
      └─ spec_to_drawio.py
```

## 安装到 Codex

将 `code-drawio-direct` 目录复制到 Codex skills 目录：

Windows:

```powershell
Copy-Item -Recurse .\code-drawio-direct $env:USERPROFILE\.codex\skills\code-drawio-direct
```

macOS / Linux:

```bash
cp -r ./code-drawio-direct ~/.codex/skills/code-drawio-direct
```

重启 Codex 后，即可在需要生成代码流程图时使用该 skill。

## 基本用法

推荐让 Codex 先结合 Serena 或代码搜索工具分析真实代码逻辑，再调用本 skill 生成图：

```text
请使用 Serena 分析当前项目中某个入口函数的真实执行流程，
再使用 code-drawio-direct 生成 draw.io 流程图。
要求输出 .diagram.json 和 .drawio，未指定路径时生成到当前目录。
```

也可以直接用脚本将 JSON 规格转换为 `.drawio`：

```powershell
python code-drawio-direct\scripts\spec_to_drawio.py code-drawio-direct\examples\api-retry.diagram.json
```

默认会在当前目录生成：

```text
api-retry.drawio
```

指定输出路径：

```powershell
python code-drawio-direct\scripts\spec_to_drawio.py code-drawio-direct\examples\api-retry.diagram.json output\api-retry.drawio
```

严格校验：

```powershell
python code-drawio-direct\scripts\spec_to_drawio.py code-drawio-direct\examples\api-retry.diagram.json --strict
```

## 输出文件

通常会生成以下文件：

```text
<flow-name>.diagram.json   图结构源文件
<flow-name>.drawio         可编辑 draw.io 文件
<flow-name>.summary.md     非简单流程的文字说明，推荐保留
```

如需导出图片或 PDF，可使用 draw.io Desktop CLI：

```powershell
drawio -x -f png -e -b 10 -o login-flow.drawio.png login-flow.drawio
```

## 依赖

- Python 3.9 或更高版本，用于运行 `spec_to_drawio.py`。
- draw.io Desktop 可选，仅在需要导出 PNG、SVG、PDF 时使用。
- Serena MCP 可选，但推荐配合使用，用于提高代码分析的准确性。

## 使用建议

- 图中只放入代码中能够确认的逻辑，不要把推测内容画成事实。
- 单页图尽量控制在 25 个节点以内，复杂流程拆成多页。
- 保留 `.diagram.json`，后续代码变化时可以基于它重新生成 `.drawio`。
- 对重试、轮询、状态机回跳等路径，优先使用 `loop: true` 或 `route: "side"`。

```
使用 $code-drawio-direct 分析现在的XXXX的代码逻辑，直接生成XXXX.drawio。
```

