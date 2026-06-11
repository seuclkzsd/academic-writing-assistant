# 学术写作规范助手（Academic Writing Assistant）

> 训练营赛道：**学习与科研赋能方向** —— 围绕"写得更规范"，服务学生 / 教师 / 科研人员的学术写作真实需求。

一个面向论文写作全流程的智能助手，提供 **论文提纲生成、学术表达润色、参考文献格式转换** 三大功能，
采用 **云端 + 本地端混合 AI 架构**，契合赛道附加分要求。

---

## 一、功能清单

| 模块 | 能力 | 落地说明 |
| --- | --- | --- |
| 论文提纲生成 | 输入题目 / 研究方向 / 论文类型，生成结构化提纲（章节 + 要点 + 写作提示） | 大模型生成，质量高，偏"重"任务 → 优先云端 |
| 学术表达润色 | 段落润色，支持多风格（严谨 / 简洁 / 流畅 / 降 AI 味），可中英 | 短文本、隐私敏感 → 优先本地小模型 |
| 参考文献格式转换 | BibTeX / 自由文本 ⇄ GB/T 7714-2015、APA 7th | **规则化实现，完全离线、确定性强、不会翻车** |
| 架构说明面板 | 实时展示当前使用的是本地还是云端，演示混合架构 | 评审演示用 |


## 二、技术架构

```
┌────────────────────────────────────────────────────────────┐
│                     Streamlit 前端 UI                        │
│        提纲生成  |  学术润色  |  参考文献  |  架构说明         │
└───────────────────────────┬────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   LLM 智能路由     │  根据任务类型 / 隐私 / 网络
                  │  (core/llm.py)    │  自动选择执行端，并支持降级
                  └────┬─────────┬────┘
        轻量/隐私敏感   │         │   高质量/重任务
              ┌─────────▼──┐  ┌───▼──────────┐
              │  本地端     │  │   云端        │
              │ Ollama      │  │ OpenAI 兼容   │
              │             │  │ (Qwen/DeepSeek│
              │ 润色/格式化 │  │  /OpenAI...)  │
              └─────────────┘  └──────────────┘
                  ▲
                  │  规则引擎（纯本地、无需模型）
          ┌───────┴────────┐
          │ 参考文献格式转换 │ core/references.py
          └────────────────┘
```

### 云端 / 本地端分工（附加分核心）

| 任务 | 设计执行端 | 原因 |
| --- | --- | --- |
| 参考文献格式转换 | **本地规则引擎** | 确定性高、无需联网、保护未发表数据 |
| 学术润色（短文本） | **本地小模型** | 文稿隐私敏感、响应快、可离线 |
| 论文提纲生成 | **云端大模型** | 需要更强的结构化与领域知识 |
| 任一端不可用 | 自动降级 | 云端失败→本地；都不可用→离线模板，保证可演示 |

`LLM_MODE` 支持 `cloud` / `auto`（智能路由）/ `local` / `mock`（纯离线演示）。

> **当前阶段说明**：实验统一使用**云端模型**（默认 `LLM_MODE=cloud`），所有模型调用直连云端，
> 需要演示"云端 + 本地端混合架构"加分项时，把 `LLM_MODE` 改为 `auto` 即可启用，无需改代码。
> 注：参考文献格式转换是纯规则引擎，无论何种模式都始终在本地执行、无需模型。

## 三、技术栈

- Python 3.10+
- [Streamlit](https://streamlit.io/) — 快速搭建演示级 Web UI
- [openai](https://pypi.org/project/openai/) SDK — 统一调用云端与本地（Ollama）OpenAI 兼容接口
- [bibtexparser](https://pypi.org/project/bibtexparser/) — 解析 BibTeX
- 本地推理（可选）：[Ollama](https://ollama.com/)，模型如 `qwen2.5:7b`

## 四、快速开始

```bash
cd academic-writing-assistant
pip install -r requirements.txt
cp .env.example .env        
streamlit run app.py
```

打开浏览器访问 `http://localhost:8501`。

> 不配置任何 Key 时，应用以 `mock` 模式运行：参考文献转换功能**完全可用**（规则化），
> 提纲/润色返回占位示例，方便先看整体效果。

### 接入云端大模型（任选其一）

`.env` 示例（以阿里云百炼 / 通义千问为例，OpenAI / DeepSeek / 火山方舟同理，改 base_url 与 model 即可）：

```env
LLM_MODE=cloud
CLOUD_API_KEY=sk-xxxx
CLOUD_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CLOUD_MODEL=qwen-plus
```


## 五、样例测试

`examples/` 下放了三类功能的输入样例，`run_examples.py` 读取它们并依次跑测试、把结果写入 `examples/output/`。

```bash
python run_examples.py                   # 跑全部（按 .env 的 LLM_MODE，默认云端）
python run_examples.py --task references  # 仅参考文献（纯本地规则、最快）
python run_examples.py --task polish --style 简洁
LLM_MODE=mock python run_examples.py      # 离线快速自测（不调模型，参考文献仍完全可用）
```

输入样例：

- `examples/outline_input.json` —— 提纲生成参数（题目 / 领域 / 类型 / 补充要求）
- `examples/polish_input.txt` —— 待润色段落
- `examples/references_input.bib` —— BibTeX（含期刊/专著/会议/学位论文/网络文献 5 类）

## 六、开发里程碑

- **M1（已完成，本骨架）**：三大功能跑通 + 混合路由 + 离线可演示。
- **M2**：参考文献支持更多类型（学位论文、标准、专利、网页）与更多格式（MLA、IEEE）。
- **M3**：提纲生成接入"逐章写作"，润色支持修订痕迹 diff 对比。
- **M4**：接入本地向量库做"个人写作风格记忆"；打包为一键运行的桌面应用。
- **M5**：内容查重辅助（基于本地语料相似度自检 + AI 味检测）。

## 七、目录结构

```
academic-writing-assistant/
├── app.py                # Streamlit 入口
├── run_examples.py       # 样例测试脚本
├── core/
│   ├── config.py         # 配置与环境变量
│   ├── llm.py            # LLM 智能路由（本地/云端/离线降级）
│   ├── outline.py        # 论文提纲生成
│   ├── polish.py         # 学术表达润色
│   └── references.py     # 参考文献解析与格式转换（规则化）
├── examples/             # 输入样例与运行结果
│   ├── outline_input.json
│   ├── polish_input.txt
│   ├── references_input.bib
│   └── output/           # 脚本生成（已 gitignore）
├── requirements.txt
├── .env.example
└── README.md
```
