# 后端技术实现说明

> 倪羽辰 | dashcam-semantic-recall 后端部分  
> 适用答辩 & 最终报告引用

---

## 1. 整体架构

```
Qt6 桌面客户端 (吕霄阳)
        │  HTTP REST (Bearer Token)
        ▼
┌─────────────────────────────────┐
│  FastAPI 后端 (apps/backend/)    │
│                                  │
│  ┌──────────┐  ┌──────────────┐ │
│  │ 鉴权层    │  │ 审计日志      │ │
│  │ JWT+bcrypt│  │ audit_logs   │ │
│  └──────────┘  └──────────────┘ │
│                                  │
│  ┌──────────────────────────────┐│
│  │        业务服务层             ││
│  │  media_pipeline  │ ffmpeg    ││
│  │  model_adapter   │ Qwen-VL   ││
│  │  event_aggregator│ 滑窗合并   ││
│  │  hybrid_search   │ 向量+关键词││
│  │  exporter        │ zip 打包   ││
│  └──────────────────────────────┘│
│                                  │
│  ┌──────────────────────────────┐│
│  │      PostgreSQL 16           ││
│  │  9 张业务表 + cosine_similarity ││
│  │  REAL[] 向量存储              ││
│  └──────────────────────────────┘│
└─────────────────────────────────┘
```

---

## 2. PostgreSQL 双引擎数据库

### 2.1 设计目标

- 生产环境使用 **PostgreSQL 16**，向量以原生 `REAL[]` 类型存储
- 开发/测试环境可一键切换回 **SQLite**（通过 `.env` 中 `DVR_SEMANTIC_DB_URL` 配置）
- 9 张业务表对齐《概要设计 V4.0》第 4 章

### 2.2 双引擎实现

```python
# db.py: 根据连接串自动适配
DATABASE_URL = os.getenv("DVR_SEMANTIC_DB_URL")  # .env 配置
IS_SQLITE = DATABASE_URL.startswith("sqlite")

# 向量列：PG 用原生 REAL[]，SQLite 用 JSON 兜底
class SemanticEvent(Base):
    if IS_SQLITE:
        embedding = Column(JSON, default=list)
    else:
        embedding = Column(ARRAY(Float), default=list)  # → PostgreSQL REAL[]
```

**优势**：
- 测试用 SQLite 内存库 (`sqlite:///:memory:`)，每个测试 session 自动隔离，不与生产 PG 冲突
- 生产用 PG，享受真实向量运算、事务隔离、并发能力

### 2.3 测试隔离

通过 `pyproject.toml` 配置 `pytest-env` 插件：

```toml
[tool.pytest.ini_options]
env = [
  "DVR_SEMANTIC_DB_URL=sqlite:///:memory:"
]
```

`load_dotenv(override=False)` 确保测试环境变量优先于 `.env` 文件，实现测试与生产完全隔离。

---

## 3. 向量检索实现

### 3.1 为什么不用 pgvector

pgvector 扩展在 Windows 上需要 Visual Studio 编译环境，增加了部署复杂度。本项目采用 **PostgreSQL 原生 `REAL[]` 数组 + PL/pgSQL 余弦相似度函数**的等效方案：

- 功能等价：余弦相似度计算与 pgvector 的 `<=>` 算子完全一致
- 当前规模足够：课程项目处理几十～几百个语义事件，无需 HNSW 索引
- 零额外依赖：无需编译任何 C 扩展

### 3.2 PostgreSQL 余弦相似度函数

```sql
CREATE OR REPLACE FUNCTION cosine_similarity(
    a double precision[], b double precision[]
) RETURNS double precision AS $$
DECLARE
    dot_product double precision := 0;
    norm_a double precision := 0;
    norm_b double precision := 0;
    i int;
BEGIN
    FOR i IN 1..array_length(a, 1) LOOP
        dot_product := dot_product + a[i] * b[i];
        norm_a := norm_a + a[i] * a[i];
        norm_b := norm_b + b[i] * b[i];
    END LOOP;
    IF norm_a = 0 OR norm_b = 0 THEN RETURN 0; END IF;
    RETURN dot_product / sqrt(norm_a * norm_b);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

### 3.3 混合检索策略

检索公式：**final = 0.6 × vector_score + 0.4 × keyword_score**

| 分量 | 权重 | 说明 |
|---|---|---|
| vector_score | 0.6 | PostgreSQL `cosine_similarity()` 在数据库内计算，384 维向量 |
| keyword_score | 0.4 | 中文关键词匹配：命中事件类型别名 +0.4、标签匹配 +0.2、标题命中 +0.2、摘要 n-gram 匹配 +0.05/词 |

**向量编码**：
- 优先使用 `sentence-transformers`（`paraphrase-multilingual-MiniLM-L12-v2`，384 维）
- 未安装时自动降级为 **hash-ngram** 确定性哈希向量（384 维，无需下载模型）

**检索流程**：

```
用户查询 "找一下违停"
    │
    ├─→ encode_text() → 384d 查询向量
    │
    ├─→ PostgreSQL: cosine_similarity(e.embedding, query_vec)
    │   对 semantic_events 表全量计算余弦相似度
    │
    ├─→ Python: _keyword_score() 关键词打分
    │
    └─→ 加权合并 → 排序 → TOP-K 返回
```

---

## 4. 多模态视觉分析

### 4.1 适配器架构

```
ModelAdapter (Protocol)
    ├── MockAdapter         → 确定性伪标签，无网络
    └── OpenAICompatibleAdapter → DeepSeek-VL / Qwen-VL
```

### 4.2 Qwen-VL 集成

采用阿里云 DashScope 的 OpenAI 兼容接口，模型名 `qwen-vl-plus`：

```python
# System Prompt（中文）
"你是一个行车记录仪画面分析助手。请判断该画面是否包含以下事件之一：
 剐蹭/碰撞、违停、道路障碍、异常停车或急刹、行人风险。
 严格用 JSON 返回..."

# 请求格式
{
    "model": "qwen-vl-plus",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": [
            {"type": "text", "text": "请分析这一帧..."},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]}
    ]
}
```

分析结果示例（来自真实行车记录仪视频）：

```json
{
  "event_type": "scratch",
  "tags": ["多车碰撞", "失控", "追尾"],
  "summary": "行车记录仪画面显示一辆轿车失控被后方车辆追尾，多车相撞。",
  "confidence": 0.95,
  "anomaly": true
}
```

网络的失败时自动回退到 mock 标签，保证演示不崩溃。

---

## 5. 事件聚合算法

### 5.1 流程

```
ffmpeg 抽取关键帧 (1帧/3秒)
    │
    ├─→ Qwen-VL 逐帧分析 → FrameAnalysis 表
    │   (event_type, tags, summary, confidence)
    │
    ├─→ 滑窗合并: 相邻 ≤10s 同类型帧 → 一个 SemanticEvent
    │   - 取最早帧为 start_sec，最晚帧为 end_sec
    │   - 取最高 confidence
    │   - 标签去重合并
    │
    └─→ 低置信度 (< 阈值) → review_status = "reviewing" → 进入人工复核队列
```

### 5.2 状态机

```
uploaded → preprocessing → analyzing → indexed
                ↓                ↓
         preprocessing_failed  analyze_failed
```

---

## 6. 人工复核 API

### 6.1 接口设计

| 方法 | 路径 | 功能 | 权限 |
|---|---|---|---|
| GET | `/api/review/tasks` | 获取复核队列 | reviewer, admin |
| POST | `/api/review/tasks/{id}/decision` | 提交复核结论 | reviewer, admin |

### 6.2 复核决策接口

```json
// 请求
POST /api/review/tasks/evt-xxx/decision
{
  "decision": "confirmed",
  "corrected_title": "多车碰撞——轿车失控追尾",
  "corrected_tags": ["多车碰撞", "追尾", "失控"],
  "note": "复核确认属实，画面清晰"
}

// 响应
{
  "event_id": "evt-xxx",
  "review_status": "confirmed",
  "reviewer_id": "usr-xxx",
  "reviewed_at": "2026-05-14T11:49:38"
}
```

每一次复核操作都会写入 `audit_logs` 表，记录操作人、操作类型、目标事件、备注信息。

---

## 7. 证据导出流程

```
POST /api/events/{id}/export
    │
    ├─→ ffmpeg 切片: start_sec−3s ~ end_sec+3s → clip.mp4
    ├─→ 关键帧截图: snapshot.jpg
    ├─→ JSON 摘要: report.json (事件元数据 + 标签 + 时间戳)
    ├─→ Markdown 摘要: report.md
    │
    └─→ zip 打包 → var/media/exports/{event_id}/package.zip
```

---

## 8. 鉴权与审计

| 组件 | 实现 |
|---|---|
| 密码哈希 | bcrypt（72 字节限制，超长密钥走 SHA-256 预处理） |
| Token | PyJWT HS256，默认 12 小时有效 |
| 角色 | user / reviewer / admin 三级，FastAPI Dependency 注入 |
| 审计 | 每次写操作写入 `audit_logs`，带 `X-Request-Id` 追踪 |

种子账号：

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |
| reviewer | review123 | 审核员 |
| demo | demo123 | 普通用户 |

---

## 9. 关键技术选型总结

| 选择 | 理由 |
|---|---|
| PostgreSQL 替代 pgvector | Windows 免编译，功能等价，当前规模无性能差异 |
| Qwen-VL-Plus 替代 DeepSeek | 单价更低（~0.04元/60s视频），原生支持 OpenAI 视觉协议 |
| hash-ngram 降级 embedding | sentence-transformers 未装时仍可运行，测试可重复 |
| Python cosine 兜底 | SQLite 路径保持兼容，测试走 SQLite 不受影响 |
