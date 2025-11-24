# 社交类APP隐私政策合规检测系统

一个自动化检测隐私政策文本合规风险的工具，可快速识别风险点并生成包含法规依据、案例参考及整改建议的合规报告。


## 核心功能
- **多源输入检测**：支持上传PDF/HTML/TXT文件或输入网页URL，自动解析隐私政策文本。
- **智能风险分析**：通过NLP模型分割文本、识别高风险片段，结合法规库和案例库评估风险等级（高/中/低）。
- **合规报告生成**：输出风险详情、违规法规、相关案例及整改建议，支持导出和历史版本对比。
- **知识库管理**：管理员可维护法规库和案例库，提升检测准确性。


## 快速开始

### 环境配置
1. 复制项目根目录的 `.env` 模板（或创建 `.env` 文件），填写实际配置：
   - 数据库（PostgreSQL、Redis、Milvus）连接信息
   - 模型接口密钥（如DashScope API Key）
   - 模型路径及参数

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 启动服务
1. 启动FastAPI服务：
   ```bash
   uvicorn main:app --reload
   ```

2. 启动Celery异步任务 worker：
   ```bash
   celery -A app.tasks.celery_app.celery_app worker --loglevel=info
   ```

3. （可选）初始化知识库数据：
   ```bash
   python data_loader.py
   ```


## 技术栈
- **后端**：FastAPI（API服务）、Celery（异步任务）
- **数据库**：PostgreSQL（结构化数据）、Redis（缓存/消息队列）、Milvus（向量检索）
- **AI模型**：BERT（文本处理）、XGBoost（风险等级预测）、DashScope API（嵌入生成/建议生成）
- **前端**：Tailwind CSS（界面展示）
