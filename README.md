# SkillCode2Drawio

`SkillCode2Drawio` 是一个面向 Codex 的 draw.io 绘图 skill 集合，用于让 AI 在分析真实代码后，生成可编辑的 diagrams.net / draw.io `.drawio` 文件。

当前包含两个 skill：

- `code-drawio-direct`：根据代码执行逻辑生成流程图、控制流图、业务流程图。
- `code-drawio-class`：根据代码中的类、结构体、接口、枚举、字段和关系生成类图/数据结构关系图。

## 主要能力

- 不依赖 Mermaid 中间格式，直接生成原生 `.drawio` XML。
- 使用简洁 JSON 作为可维护的中间规格文件。
- 支持 Codex 先结合 CodeGraph、Serena 或代码搜索工具分析真实代码，再生成图。
- 生成的 `.drawio` 文件可以继续用 draw.io Desktop、diagrams.net 或 VS Code draw.io 插件编辑。

## 目录结构

```text
SkillCode2Drawio/
├─ README.md
├─ code-drawio-direct/
│  ├─ SKILL.md
│  ├─ agents/
│  ├─ examples/
│  ├─ references/
│  └─ scripts/
│     └─ spec_to_drawio.py
└─ code-drawio-class/
   ├─ SKILL.md
   ├─ agents/
   ├─ references/
   └─ scripts/
      └─ class_spec_to_drawio.py
```

## 安装到 Codex

将需要的 skill 目录复制到 Codex skills 目录。

Windows:

```powershell
Copy-Item -Recurse .\code-drawio-direct $env:USERPROFILE\.codex\skills\code-drawio-direct
Copy-Item -Recurse .\code-drawio-class  $env:USERPROFILE\.codex\skills\code-drawio-class
```

macOS / Linux:

```bash
cp -r ./code-drawio-direct ~/.codex/skills/code-drawio-direct
cp -r ./code-drawio-class ~/.codex/skills/code-drawio-class
```

重启 Codex 后即可使用。

## 使用示例

生成代码流程图：

```text
请使用 CodeGraph 或 Serena 分析当前项目中某个入口函数的真实执行流程，
再使用 code-drawio-direct 生成 draw.io 流程图。
要求输出 .diagram.json 和 .drawio，未指定路径时生成到当前目录。
```

生成类图/结构关系图：

```text
请使用 CodeGraph 或 Serena 分析 StruInnerElem 相关的数据结构、字段、方法和引用关系，
再使用 code-drawio-class 生成 draw.io 类图。
要求区分继承、组合、聚合、关联和依赖关系。
```

## 直接运行脚本

流程图：

```powershell
python code-drawio-direct\scripts\spec_to_drawio.py code-drawio-direct\examples\api-retry.diagram.json
```

类图：

```powershell
python code-drawio-class\scripts\class_spec_to_drawio.py code-drawio-class\references\example.class-diagram.json
```

指定输出路径：

```powershell
python code-drawio-class\scripts\class_spec_to_drawio.py code-drawio-class\references\example.class-diagram.json output\order-model.drawio
```

严格校验：

```powershell
python code-drawio-class\scripts\class_spec_to_drawio.py code-drawio-class\references\example.class-diagram.json --strict
```

## 输出文件

流程图通常生成：

```text
<flow-name>.diagram.json
<flow-name>.drawio
<flow-name>.summary.md
```

类图通常生成：

```text
<diagram-name>.class-diagram.json
<diagram-name>.drawio
<diagram-name>.summary.md
```

## 依赖

- Python 3.9 或更高版本。
- draw.io Desktop 可选，仅在需要导出 PNG、SVG、PDF 时使用。
- CodeGraph 或 Serena 可选但推荐，用于提高代码分析准确性。

## 使用建议

- 先分析真实代码，再生成图，不要凭猜测补关系。
- 流程图用 `code-drawio-direct`。
- 类图、结构体图、数据模型关系图用 `code-drawio-class`。
- 保留 JSON 规格文件，后续代码变化时可以基于它重新生成 `.drawio`。
- 对不确定的关系，在 summary 中标注，不要直接画成确定事实。
