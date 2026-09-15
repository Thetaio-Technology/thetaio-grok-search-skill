# ThetaIO Grok Search — README 视觉素材 brief

## 用途

为 GitHub 仓库 `thetaio-grok-search-skill` 的 README 生成视觉素材：一张 hero 主图 + 两三张辅助图。

## 品牌约束（来自 THETAIO_DESIGN_SYSTEM.md）

- **主色**：近黑 `#090909` / `#050505` / `#101010`，纸张灰 `#f3f2ee` / `#f7f6f2` / `#e7e5df`
- **层级**：细边框 `#cfcdc6`，无强阴影（除品牌深色核心视觉对象）
- **语义色**：钩子绿 `#b9c7a7`（仅用于"已连接/已验证/在线"可信状态，少量），成功绿 `#059669` 极少量
- **字体气质**：Outfit（品牌/编号/系统标签，大写小字号宽字距）、Plus Jakarta Sans（主标题，中等字重 540–560，非 700–900）、Georgia（编辑式强调）、等宽（API/模型/路径）
- **构图**：基础设施线路图、系统面板节点、编辑式排版、信息档案感
- **核心规则**：
  - ❌ 不用紫蓝渐变、霓虹发光、抽象 AI 人物、发光球体、高饱和科技感
  - ❌ 不用大圆角悬浮卡片堆叠
  - ✅ 用近黑背景 + 细灰线路 + 小节点面板 + 英文大写系统标签
  - ✅ 边缘小圆角（3–8px）或直角，工业化
  - ✅ 克制、精确、私密、可信

## 素材清单

| # | 文件 | 比例 | 内容 |
|---|---|---|---|
| 01 | `hero.png` | 16:9 | Hero 主图：近黑基础设施线路图，中心为搜索/数据流节点，两端是 X 与 Web 信源 |
| 02 | `pipeline.png` | 16:9 | 请求管线图：client → thetaio gateway → grok x_search/web_search → citations |
| 03 | `mono-dark.png` | 1:1 | 深色方形：`x_search` / `web_search` 两条并行工具链的档案式卡片 |
| 04 | `status.png` | 3:1 | 细长状态条：模拟 usage 面板，`x_search_calls: 3` 等真实运行数据 |

## 文字策略

图内文字仅使用可确认的英文系统标签（大写）与代码标识：
`THETAIO`, `GROK SEARCH`, `X_SEARCH`, `WEB_SEARCH`, `POST /V1/RESPONSES`, `MODEL: GROK-4.3`,
`URL_CITATION`, `ONLINE`, `CALLS: 3`。不编造营销文案，不放大段汉字。
