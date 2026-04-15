# 阶段四完成总结（患者管理部分）

## ✅ 已完成功能

### 1. 患者管理服务 (`patient_service.py`)

#### 1.1 患者编号自动生成
- **格式**：P + 年月日 + 4位序号
- **示例**：P202602100001, P202602100002
- **特点**：
  - 每天从0001开始递增
  - 自动查询当天最后一个编号
  - 避免编号冲突

#### 1.2 患者 CRUD 操作
- **创建患者**：自动生成患者编号，关联医生
- **查询患者**：按ID或患者编号查询
- **更新患者**：更新患者基本信息
- **删除患者**：删除患者记录
- **列表查询**：
  - 支持分页（skip/limit）
  - 支持搜索（姓名、患者编号、手机号）
  - 医生只能看到自己的患者
  - 管理员可以看到所有患者

#### 1.3 预测记录管理
- **创建预测记录**：关联患者和用户
- **查询预测记录**：获取患者的所有预测记录
- **更新医生备注**：医生可以为预测记录添加诊断意见

#### 1.4 患者统计信息
- **预测次数统计**：
  - 总预测次数
  - 高/中/低风险次数
- **最近一次预测**：
  - 预测结果
  - 风险等级
  - 概率
  - 预测时间
- **风险趋势**：最近10次预测的风险变化

#### 1.5 随访管理
- **随访条件**：
  - 距离上次预测超过指定天数（默认30天）
  - 或最近一次预测为高风险
- **随访信息**：
  - 患者基本信息
  - 上次预测日期
  - 距今天数
  - 最近风险等级
  - 随访原因（高风险/超期）

---

### 2. 患者管理 API (`patients.py`)

#### 2.1 API 接口列表

| 接口 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/v1/patients` | POST | 医生 | 创建患者 |
| `/api/v1/patients` | GET | 登录用户 | 获取患者列表 |
| `/api/v1/patients/{id}` | GET | 登录用户 | 获取患者详情 |
| `/api/v1/patients/{id}` | PUT | 医生 | 更新患者信息 |
| `/api/v1/patients/{id}` | DELETE | 医生 | 删除患者 |
| `/api/v1/patients/{id}/predictions` | GET | 登录用户 | 获取患者预测记录 |
| `/api/v1/patients/{id}/statistics` | GET | 登录用户 | 获取患者统计信息 |
| `/api/v1/patients/follow-up/list` | GET | 医生 | 获取需要随访的患者 |
| `/api/v1/patients/predictions/{id}/notes` | PUT | 医生 | 更新预测记录备注 |

#### 2.2 权限控制
- **医生权限**：
  - 只能查看/编辑/删除自己的患者
  - 可以为自己患者的预测记录添加备注
- **管理员权限**：
  - 可以查看所有患者
  - 可以管理所有患者信息
- **患者权限**：
  - 只能查看自己的信息（未实现，待扩展）

#### 2.3 数据验证
- 患者姓名、性别、年龄必填
- 手机号格式验证
- 身份证号格式验证（可选）
- 年龄范围验证（0-150）

---

### 3. 前端患者管理界面

#### 3.1 患者列表页面 (`PatientList.vue`)

**功能特性**：
- **搜索功能**：
  - 支持按姓名、患者编号、手机号搜索
  - 实时搜索，按回车或点击搜索按钮
- **患者列表**：
  - 表格展示患者信息
  - 显示患者编号、姓名、性别、年龄、手机号、主治医生、创建时间
  - 支持分页（10/20/50/100条/页）
- **操作按钮**：
  - 查看：跳转到患者详情页
  - 编辑：弹出编辑对话框（仅医生和管理员）
  - 删除：删除患者（仅医生和管理员）
- **添加患者**：
  - 弹出对话框，填写患者信息
  - 表单验证（姓名必填、手机号格式等）
  - 自动生成患者编号

**权限控制**：
- 医生和管理员可以添加、编辑、删除患者
- 医生只能看到自己的患者
- 管理员可以看到所有患者

#### 3.2 患者详情页面 (`PatientDetail.vue`)

**功能模块**：

1. **基本信息卡片**：
   - 显示患者完整信息
   - 使用 el-descriptions 组件展示
   - 包括：患者编号、姓名、性别、年龄、出生日期、身份证号、手机号、地址、紧急联系人、病史、过敏史、备注等

2. **统计信息卡片**：
   - **预测统计**：
     - 总预测次数
     - 高/中/低风险次数（带颜色标识）
   - **最近一次预测**：
     - 预测结果
     - 风险等级（带标签）
     - 概率
     - 预测时间
   - **风险趋势图**：
     - 使用 ECharts 绘制折线图
     - 显示最近10次预测的风险概率变化
     - 带渐变填充效果

3. **预测记录表格**：
   - 显示所有预测记录
   - 包括：ID、模型、预测结果、风险等级、概率、医生备注、预测时间
   - 支持分页（10/20/50条/页）
   - 医生可以编辑备注

4. **操作功能**：
   - 返回按钮：返回患者列表
   - 编辑按钮：编辑患者信息（仅医生和管理员）
   - 新建预测按钮：跳转到预测页面
   - 编辑备注：为预测记录添加医生意见

**数据可视化**：
- 使用 ECharts 绘制风险趋势图
- 折线图 + 面积图
- 自动适配数据范围
- 响应式设计

---

### 4. 路由配置

#### 4.1 后端路由
```python
# backend/app/main.py
app.include_router(patients.router, prefix=settings.API_V1_PREFIX, tags=["患者管理"])
```

#### 4.2 前端路由
```javascript
// frontend/src/router/index.js
{
  path: '/patients',
  name: 'PatientList',
  component: () => import('../views/PatientList.vue'),
  meta: { requiresAuth: true, roles: ['admin', 'doctor'] }
},
{
  path: '/patients/:id',
  name: 'PatientDetail',
  component: () => import('../views/PatientDetail.vue'),
  meta: { requiresAuth: true, roles: ['admin', 'doctor'] }
}
```

#### 4.3 导航菜单
```vue
<!-- frontend/src/App.vue -->
<el-menu-item index="/patients" v-if="canManagePatients">患者管理</el-menu-item>
```

---

## 📁 新增/修改文件列表

### 后端 (2个文件)
```
backend/
├── app/
│   ├── services/
│   │   └── patient_service.py          # 患者管理服务（~457行）
│   ├── api/v1/
│   │   └── patients.py                 # 患者管理 API（~375行）
│   └── main.py                         # 注册患者路由（修改）
```

### 前端 (4个文件)
```
frontend/
└── src/
    ├── views/
    │   ├── PatientList.vue             # 患者列表页面（~380行）
    │   └── PatientDetail.vue           # 患者详情页面（~450行）
    ├── router/
    │   └── index.js                    # 添加患者路由（修改）
    └── App.vue                         # 添加患者菜单（修改）
```

---

## 🔬 功能详解

### 1. 患者编号生成示例

```python
from app.services.patient_service import PatientService

service = PatientService(db)

# 生成患者编号
patient_no = service.generate_patient_no()
# 输出: P202602100001

# 创建患者
patient = service.create_patient(
    patient_data=PatientCreate(
        name="张三",
        gender="male",
        age=55,
        phone="13800138000"
    ),
    doctor_id=1  # 医生ID
)

print(f"患者编号: {patient.patient_no}")
# 输出: 患者编号: P202602100001
```

### 2. 患者列表查询示例

```python
# 医生查询自己的患者
patients, total = service.list_patients(
    doctor_id=1,
    search="张",
    skip=0,
    limit=20
)

print(f"找到 {total} 个患者")
for patient in patients:
    print(f"{patient.patient_no} - {patient.name}")
```

### 3. 患者统计信息示例

```python
# 获取患者统计
statistics = service.get_patient_statistics(patient_id=1)

print(f"总预测次数: {statistics['prediction_statistics']['total_predictions']}")
print(f"高风险次数: {statistics['prediction_statistics']['high_risk_count']}")
print(f"最近一次预测: {statistics['latest_prediction']}")
print(f"风险趋势: {statistics['risk_trend']}")
```

**输出示例**：
```json
{
  "patient_info": {
    "patient_no": "P202602100001",
    "name": "张三",
    "age": 55,
    "gender": "male"
  },
  "prediction_statistics": {
    "total_predictions": 15,
    "high_risk_count": 3,
    "medium_risk_count": 7,
    "low_risk_count": 5
  },
  "latest_prediction": {
    "id": 45,
    "prediction": 1,
    "probability": "0.75",
    "risk_level": "high",
    "created_at": "2026-02-10T10:30:00"
  },
  "risk_trend": [
    {"date": "2026-02-01", "risk_level": "medium", "probability": "0.55"},
    {"date": "2026-02-03", "risk_level": "high", "probability": "0.72"},
    ...
  ]
}
```

### 4. 随访患者查询示例

```python
# 获取需要随访的患者
follow_up_list = service.get_follow_up_patients(
    doctor_id=1,
    days=30  # 30天未预测
)

print(f"需要随访的患者: {len(follow_up_list)}")
for patient in follow_up_list:
    print(f"{patient['name']} - {patient['reason']} - {patient['days_since_last']}天")
```

**输出示例**：
```json
[
  {
    "patient_id": 1,
    "patient_no": "P202602100001",
    "name": "张三",
    "phone": "13800138000",
    "last_prediction_date": "2026-01-05",
    "days_since_last": 36,
    "last_risk_level": "medium",
    "reason": "overdue"
  },
  {
    "patient_id": 2,
    "patient_no": "P202602100002",
    "name": "李四",
    "phone": "13800138001",
    "last_prediction_date": "2026-02-08",
    "days_since_last": 2,
    "last_risk_level": "high",
    "reason": "high_risk"
  }
]
```

---

## 📊 数据模型

### Patient 模型
```python
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_no = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    gender = Column(Enum('male', 'female'), nullable=False)
    age = Column(Integer, nullable=False)
    birth_date = Column(Date, nullable=True)
    id_card = Column(String(18), nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    emergency_contact = Column(String(50), nullable=True)
    emergency_phone = Column(String(20), nullable=True)
    medical_history = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    doctor_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
```

---

## 🎯 使用场景

### 场景 1：医生添加新患者
```
1. 医生登录系统
2. 点击"患者管理"菜单
3. 点击"添加患者"按钮
4. 填写患者信息（姓名、性别、年龄、手机号等）
5. 提交表单
6. 系统自动生成患者编号（如 P202602100001）
7. 患者自动关联到该医生
```

### 场景 2：查看患者详情和统计
```
1. 在患者列表中点击"查看"按钮
2. 进入患者详情页
3. 查看患者基本信息
4. 查看预测统计（总次数、风险分布）
5. 查看风险趋势图（最近10次）
6. 查看所有预测记录
7. 为预测记录添加医生备注
```

### 场景 3：随访管理
```
1. 医生点击"患者管理" -> "随访列表"（待实现）
2. 系统显示需要随访的患者
3. 包括：
   - 超过30天未预测的患者
   - 最近一次预测为高风险的患者
4. 医生可以联系患者进行随访
5. 为患者创建新的预测记录
```

### 场景 4：患者搜索
```
1. 在患者列表页面
2. 输入搜索关键词（姓名/患者编号/手机号）
3. 按回车或点击搜索按钮
4. 系统返回匹配的患者列表
5. 支持模糊搜索
```

---

## 💡 最佳实践

### 1. 患者编号管理
- 每天从0001开始递增
- 格式统一：P + YYYYMMDD + 序号
- 避免手动输入，使用自动生成
- 患者编号唯一，不可重复

### 2. 权限控制
- 医生只能管理自己的患者
- 管理员可以管理所有患者
- 患者只能查看自己的信息（待实现）
- 使用 `require_doctor` 依赖注入确保权限

### 3. 数据验证
- 必填字段：姓名、性别、年龄
- 手机号格式验证
- 年龄范围验证（0-150）
- 身份证号格式验证（可选）

### 4. 随访管理
- 定期检查需要随访的患者
- 高风险患者优先随访
- 超过30天未预测的患者需要随访
- 记录随访结果和医生备注

### 5. 数据可视化
- 使用 ECharts 绘制风险趋势图
- 清晰展示患者风险变化
- 帮助医生做出诊断决策
- 支持导出报告（待实现）

---

## 📝 API 使用示例

### 1. 创建患者

```bash
curl -X POST http://localhost:8000/api/v1/patients \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "张三",
    "gender": "male",
    "age": 55,
    "phone": "13800138000",
    "address": "北京市朝阳区",
    "medical_history": "高血压10年",
    "allergies": "青霉素过敏"
  }'
```

### 2. 获取患者列表

```bash
curl -X GET "http://localhost:8000/api/v1/patients?search=张&skip=0&limit=20" \
  -H "Authorization: Bearer <token>"
```

### 3. 获取患者详情

```bash
curl -X GET http://localhost:8000/api/v1/patients/1 \
  -H "Authorization: Bearer <token>"
```

### 4. 获取患者统计

```bash
curl -X GET http://localhost:8000/api/v1/patients/1/statistics \
  -H "Authorization: Bearer <token>"
```

### 5. 获取随访列表

```bash
curl -X GET "http://localhost:8000/api/v1/patients/follow-up/list?days=30" \
  -H "Authorization: Bearer <token>"
```

### 6. 更新预测备注

```bash
curl -X PUT "http://localhost:8000/api/v1/patients/predictions/1/notes?doctor_notes=建议复查" \
  -H "Authorization: Bearer <token>"
```

---

## 🎉 阶段四（患者管理部分）总结

已完成：
- ✅ 患者管理服务（CRUD、统计、随访）
- ✅ 患者管理 API（9个接口）
- ✅ 患者列表页面（搜索、分页、添加、编辑、删除）
- ✅ 患者详情页面（基本信息、统计、趋势图、预测记录）
- ✅ 权限控制（医生/管理员）
- ✅ 路由配置（前后端）
- ✅ 导航菜单集成

**新增代码量：~1662行**
- 后端：~832行（patient_service.py + patients.py）
- 前端：~830行（PatientList.vue + PatientDetail.vue）

---

## 📝 待完成功能（阶段四剩余部分）

### 1. 报告增强
- PDF 报告生成
- 报告模板设计
- 邮件发送功能
- 报告历史记录

### 2. 模型版本管理
- 模型版本记录
- 模型对比功能
- 模型回滚功能
- 模型性能追踪

### 3. 数据可视化增强
- 更多图表类型
- 交互式图表
- 数据导出功能
- 自定义报表

---

## 📝 下一步

继续完成阶段四的剩余功能：
1. 报告增强（PDF生成、邮件发送）
2. 模型版本管理
3. 数据可视化增强

或者进入阶段五：
- API 限流
- 监控告警
- 多语言支持
- 系统优化和测试
