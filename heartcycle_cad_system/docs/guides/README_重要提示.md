# ⚠️ 重要提示

## H5文件上传功能已修复

如果遇到以下错误：
```
无法读取HDF5文件: "Unable to synchronously open object (object 'measure' doesn't exist)"
```

**解决方案：重启后端服务**

```bash
# 1. 停止后端（在后端终端按 Ctrl+C）

# 2. 重启后端
cd "D:\Graduate Work\heartcycle_cad_system"
python scripts/start_backend.py
```

详细说明见：[H5上传问题快速修复.md](../notes/H5上传问题快速修复.md)

---

## 已修复的问题

✅ 后端代码已更新，支持简单格式的H5文件
✅ 测试数据已重新生成，包含真实的ECG信号
✅ R波检测功能正常工作
✅ 特征提取功能正常工作

**但需要重启后端服务才能生效！**

---

## 测试数据位置

所有测试文件在 `测试数据/` 目录：

- **心电样本**：`测试数据/ecg_samples/sample_001.h5`
- **训练样本**：`测试数据/h5_training_samples/`
- **批量预测**：`测试数据/batch_predict_sample.csv`
- **实验数据**：`测试数据/experiment_dataset.csv`

---

**快速开始：** 查看 [快速使用指南.md](./快速使用指南.md)
**完整手册：** 查看 [前端操作手册.md](./前端操作手册.md)
