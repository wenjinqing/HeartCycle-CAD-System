# 截图说明

本目录用于存放项目功能截图，供主README展示使用。

## 📸 需要的截图列表

### 1. 基础页面
- [ ] `banner.png` - 项目横幅图（可选，或使用logo）
- [ ] `login.png` - 登录页面
- [ ] `home.png` - 首页/导航页面

### 2. 预测功能
- [ ] `predict-single.png` - 单样本预测界面（包含输入表单和预测结果）
- [ ] `predict-batch.png` - 批量预测界面（CSV上传和结果展示）

### 3. 模型训练
- [ ] `train-wizard.png` - 训练向导界面（步骤导航）
- [ ] `train-results.png` - 训练结果页面（显示准确率、精确率等指标）
- [ ] `confusion-matrix.png` - 混淆矩阵可视化

### 4. ECG信号处理
- [ ] `h5-visualize.png` - ECG波形可视化（多导联波形图）
- [ ] `hrv-features.png` - HRV特征提取结果展示

### 5. 可解释性
- [ ] `shap-waterfall.png` - SHAP瀑布图（单样本特征贡献）
- [ ] `shap-global.png` - SHAP全局特征重要性图

### 6. 模型管理
- [ ] `model-versions.png` - 模型版本库列表

### 7. 患者管理
- [ ] `patients-list.png` - 患者列表页面
- [ ] `patient-detail.png` - 患者详情页面

### 8. 系统监控
- [ ] `dashboard.png` - 管理仪表盘（系统概览）
- [ ] `system-monitor.png` - 系统监控详情（CPU/内存/磁盘图表）

## 📐 截图规范

### 尺寸建议
- **横幅图**: 1200x400px
- **功能截图**: 1920x1080px 或 1440x900px
- **局部截图**: 根据实际内容调整

### 格式要求
- 格式: PNG（推荐）或 JPG
- 清晰度: 高清，避免模糊
- 内容: 使用测试数据，避免真实患者信息

### 截图技巧
1. **使用浏览器开发者工具**调整窗口大小到标准尺寸
2. **隐藏敏感信息**（如真实姓名、身份证号等）
3. **展示关键功能**，确保界面元素清晰可见
4. **使用测试数据**，数据要合理且有代表性
5. **保持界面整洁**，关闭不必要的浏览器插件和通知

### 截图工具推荐
- Windows: Snipping Tool / Snip & Sketch / ShareX
- Mac: Command + Shift + 4
- 浏览器插件: Awesome Screenshot, Nimbus Screenshot

## 🎨 美化建议

### 可选的图片处理
1. **添加阴影**: 让截图更有层次感
2. **添加边框**: 1-2px的浅色边框
3. **标注重点**: 使用箭头或高亮标注关键功能
4. **统一风格**: 保持所有截图的风格一致

### 在线工具
- [Carbon](https://carbon.now.sh/) - 代码截图美化
- [Screely](https://www.screely.com/) - 添加浏览器窗口框架
- [MockUPhone](https://mockuphone.com/) - 设备框架

## 📝 截图后的操作

1. 将截图文件放入本目录
2. 确保文件名与README中引用的名称一致
3. 检查图片大小（建议单张不超过500KB）
4. 如果图片过大，使用压缩工具：
   - [TinyPNG](https://tinypng.com/)
   - [Squoosh](https://squoosh.app/)

## 🔄 更新README

如果添加了新的截图，记得在主README中添加对应的引用：

```markdown
![描述文字](docs/screenshots/文件名.png)
```

## ⚠️ 注意事项

1. **不要上传包含真实患者数据的截图**
2. **不要上传包含敏感信息的截图**（如密钥、密码等）
3. **使用测试账号和测试数据**进行截图
4. **定期更新截图**，确保与最新版本界面一致
