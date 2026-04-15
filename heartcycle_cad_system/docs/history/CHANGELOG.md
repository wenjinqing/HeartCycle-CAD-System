# 更新日志

## 2026-03-04 - H5文件特征提取功能修复

### 问题
- 用户上传H5文件后无法提取特征
- 后端代码只支持HeartCycle标准格式

### 修复内容

#### 1. 后端代码修改
- **文件：** `backend/algorithms/data_processing.py`
- **修改：** `ECGProcessor.load_hdf5_file()` 方法
- **功能：** 支持简单格式和HeartCycle标准格式的H5文件

#### 2. 测试数据改进
- **文件：** `scripts/generate_test_data.py`
- **修改：** `generate_ecg_signal()` 函数
- **改进：** 生成更真实的ECG信号（包含P波、QRS波群、T波）

#### 3. 新增测试工具
- **文件：** `scripts/test_h5_extraction.py`
- **功能：** 验证H5文件特征提取功能

### 测试结果
✅ 所有测试通过（3/3个文件）
- H5文件加载正常
- R波检测成功
- 特征提取成功

### 影响范围
- 风险监测功能（`/monitor`）
- H5快速训练功能（`/train-h5-auto`）
- 深度学习训练功能（`/train-deep-learning`）

### 使用建议
1. 重新生成测试数据：`python scripts/generate_test_data.py`
2. 运行测试验证：`python scripts/test_h5_extraction.py`
3. 在前端测试上传功能

---

## 2026-03-04 - 文档和测试数据创建

### 新增文档
1. **docs/guides/前端操作手册.md** - 15个功能模块的详细操作说明
2. **docs/guides/快速使用指南.md** - 5分钟快速上手
3. **文档导航.md**（根目录，指向 docs）- 文档总览和快速导航
4. **docs/notes/H5特征提取修复说明.md** - 问题修复详细说明

### 测试数据
生成完整的测试数据集：
- 4个测试账号（JSON）
- 5个示例患者（JSON）
- 10个心电样本（H5）
- 20个训练样本（H5 + 元数据CSV）
- 5个MATLAB格式样本（H5）
- 10个批量预测样本（CSV）
- 1000个实验数据集样本（CSV）

### 测试工具
- `scripts/generate_test_data.py` - 自动生成所有测试数据
- `scripts/test_h5_extraction.py` - 验证H5特征提取功能

---

**维护者：** Claude Sonnet 4.6
**项目：** HeartCycle 冠心病风险预测系统
