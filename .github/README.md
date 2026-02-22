# 八字微服务 AWS Lambda 部署

> **Python 3.14** | **AWS Lambda + API Gateway**

八字排盘、生肖合婚、罗喉日时计算的 REST API 服务。

## 🚀 快速开始

### 1. 配置 AWS 凭证

复制配置文件模板:
```bash
cp config.toml.example config.toml
```

编辑 `config.toml` 填入你的信息:
```toml
[aws]
access_key_id = "你的_AWS_ACCESS_KEY_ID"
secret_access_key = "你的_AWS_SECRET_ACCESS_KEY"
region = "你的区域"  # 例如: us-east-1, ap-northeast-1

[lambda]
function_name = "bazi-microservice"
layer_name = "bazi-dependencies"
memory_size = 512
timeout = 30
```

**重要**: `config.toml` 已在 `.gitignore` 中，不会被提交到 git。

### 2. 部署

```bash
chmod +x scripts/auto_deploy.sh
./scripts/auto_deploy.sh
```

### 3. 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/unit -v

# 运行集成测试
python -m pytest tests/integration -v

# 运行测试覆盖率
python -m pytest tests/ --cov=app --cov-report=term-missing
```

部署前确保所有测试通过。

## 🔗 Lambda 直接调用

除了通过 API Gateway 的 HTTP 调用，现在支持从另一个 Lambda 函数直接调用！

### 快速示例

```python
import json
import boto3

lambda_client = boto3.client('lambda', region_name='us-east-1')

# 准备输入数据（直接传 JSON，会自动识别是八字服务）
bazi_input = {
    "service": "bazi",  # 可选，自动识别也可不写
    "year": 1990,
    "month": 9,
    "day": 11,
    "hour": 11,
    "isGregorian": True,
    "isFemale": False,
}

# 调用 bazi Lambda
response = lambda_client.invoke(
    FunctionName='bazi-microservice',  # 或使用 ARN
    InvocationType='RequestResponse',
    Payload=json.dumps(bazi_input)  # 注意：不需要 .encode('utf-8')
)

# 解析结果（直接返回 JSON，无需处理 HTTP 格式）
bazi_output = json.loads(response['Payload'].read().decode('utf-8'))

if bazi_output['success']:
    print(f"八字: {bazi_output['data']['bazi']['full']}")
    print(f"生肖: {bazi_output['data']['zodiac']['year']}")
```

### 服务识别规则

Lambda 会**自动识别**你要调用哪个服务（无需指定 path）：

| 参数 | 识别为 | 示例 |
|------|--------|------|
| `year` + `month` + `day` + `hour` | 八字服务 | `{"year": 1990, "month": 9, "day": 11, "hour": 11}` |
| `zodiac` 或 `shengxiao` | 生肖服务 | `{"zodiac": "虎"}` |
| `startDate` 或 `start` | 罗喉服务 | `{"startDate": "2026-02-01"}` |

**可选**：也可以明确指定 `service` 参数：
```python
{"service": "bazi", "year": 1990, "month": 9, "day": 11, "hour": 11}
```

### 优势

- ✅ **更低延迟** - 跳过 API Gateway，直接 Lambda to Lambda 调用
- ✅ **更简单** - 无需处理 HTTP 请求/响应格式，直接传 JSON
- ✅ **自动识别** - 根据参数自动判断服务类型，无需指定 path
- ✅ **内部服务** - 无需公开 API，更安全

### 响应格式对比

**API Gateway 调用**（HTTP 格式）:
```json
{
  "statusCode": 200,
  "headers": {...},
  "body": "{\"success\": true, \"data\": {...}}"
}
```

**直接 Lambda 调用**（纯 JSON）:
```json
{
  "success": true,
  "data": {
    "bazi": {"full": "庚午 甲申 癸未 甲午", ...},
    "zodiac": {"year": "马", ...},
    ...
  },
  "timestamp": "2026-02-22T10:00:00Z"
}
```

### IAM 权限

调用方 Lambda 需要有以下权限：

```json
{
  "Effect": "Allow",
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:bazi-microservice"
}
```

## 📋 API 端点

| 端点 | 方法 | 功能 | 参数 | 状态 |
|------|------|------|------|------|
| `/health` | GET | 健康检查 | 无 | ✅ |
| `/bazi` | POST | 八字排盘 | year, month, day, hour, isGregorian (默认true公历), isFemale (默认false), isLeap (默认false) | ✅ |
| `/shengxiao` | GET | 生肖合婚 | zodiac (鼠牛虎兔龙蛇马羊猴鸡狗猪) | ✅ |
| `/luohou` | GET | 罗喉日时 | startDate, endDate (YYYY-MM-DD) | ⚠️ 需要 sxtwl |

> **注意**: 罗喉功能需要 `sxtwl` 包，该包需要 C++ 编译环境。如不需要此功能，可跳过。

### 八字计算示例

**请求**:
```
POST /bazi
Content-Type: application/json
```

**参数说明**:
- `year`, `month`, `day`, `hour`: 必填，出生年月日时
- `isGregorian`: 可选，是否为公历（默认 `true`）。`true` 表示输入的是公历日期，`false` 表示输入的是农历日期
- `isFemale`: 可选，是否为女性（默认 `false`）
- `isLeap`: 可选，是否为闰月，仅在 `isGregorian=false` 时使用（默认 `false`）

**公历日期示例（默认）**:
```json
{
  "year": 1990,
  "month": 5,
  "day": 15,
  "hour": 14,
  "isGregorian": true,
  "isFemale": false
}
```

> 💡 **提示**: 由于大多数人使用公历，`isGregorian` 默认为 `true`。如果不指定，系统会将输入视为公历日期。

**农历日期示例**:
```json
{
  "year": 1990,
  "month": 5,
  "day": 15,
  "hour": 14,
  "isGregorian": true,
  "isFemale": false
}
```

**农历日期示例**:
```json
{
  "year": 1990,
  "month": 4,
  "day": 21,
  "hour": 14,
  "isGregorian": false,
  "isFemale": false
}
```

**公历日期响应示例**:
```json
{
  "success": true,
  "data": {
    "solar": {"year": 1990, "month": 5, "day": 15},
    "lunar": {"year": 1990, "month": 4, "day": 21},
    "bazi": {
      "year": {"pillar": "庚午", "gan": "庚", "zhi": "午"},
      "month": {"pillar": "辛巳", "gan": "辛", "zhi": "巳"},
      "day": {"pillar": "癸未", "gan": "癸", "zhi": "未"},
      "time": {"pillar": "己未", "gan": "己", "zhi": "未"},
      "full": "庚午 辛巳 癸未 己未"
    },
    "zodiac": {"year": "马", "day": "羊"}
  }
}
```

### 生肖合婚示例

**请求**:
```
GET /shengxiao?zodiac=虎
```

**响应**:
```json
{
  "success": true,
  "data": {
    "zodiac": "虎",
    "compatible": {
      "sanhe": ["马", "狗"],
      "liuhe": ["猪"]
    },
    "incompatible": {
      "chong": ["猴"],
      "xing": ["蛇"]
    }
  }
}
```

## 🔧 GitHub Actions 自动部署

### 配置 GitHub Secrets

仓库设置 → Secrets and variables → Actions → New repository secret

| Secret 名称 | 说明 |
|------------|------|
| `AWS_ACCESS_KEY_ID` | 你的 AWS Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | 你的 AWS Secret Access Key |
| `AWS_REGION` | 你的 AWS 区域 (例如: us-east-1) |

### 自动部署

推送到 master 分支自动触发部署:
```bash
git push origin master
```

### 手动部署

1. GitHub → Actions → "Deploy to AWS Lambda"
2. "Run workflow" → 选择分支
3. 点击 "Run workflow"

## 📊 监控日志

```bash
# 实时日志
aws logs tail /aws/lambda/bazi-microservice --follow

# 查看最近 1 小时
aws logs filter-log-events \
  --log-group-name /aws/lambda/bazi-microservice \
  --start-time $(date -d '1 hour ago' +%s)000
```

日志前缀说明:
- `[LAMBDA]` - Lambda 处理器事件
- `[BAZI]` - 八字计算步骤
- `[SHENGXIAO]` - 生肖兼容性
- `[ERROR]` - 错误详情

## 🔄 更新部署

### 方式 1: 本地脚本
```bash
./scripts/auto_deploy.sh
```

### 方式 2: GitHub Actions
```bash
git push origin master
```

### 方式 3: AWS CLI
```bash
aws lambda update-function-code \
  --function-name bazi-microservice \
  --zip-file fileb://bazi-lambda.zip
```

## 📦 项目结构

```
bazi_microservice/
├── app.py                          # Lambda 主处理器
├── config.toml.example             # 配置文件模板
├── requirements.txt                # Python 依赖
├── pyproject.toml                  # pytest 配置
├── tests/                          # 测试目录
│   ├── unit/                       # 单元测试
│   │   └── test_services.py       # 服务类测试
│   └── integration/                # 集成测试
│       └── test_api.py            # API 端点测试
├── scripts/
│   └── auto_deploy.sh             # 自动部署脚本
├── .github/
│   └── workflows/
│       ├── deploy.yml             # 部署工作流
│       └── test.yml               # 测试工作流
├── bazi.py                        # 八字计算模块
├── shengxiao.py                   # 生肖模块
├── luohou.py                      # 罗喉模块
└── ganzhi.py                      # 干支系统
```

## 🧪 测试

### 本地运行测试

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试（测试服务类）
python -m pytest tests/unit -v

# 运行集成测试（测试 API）
python -m pytest tests/integration -v

# 查看测试覆盖率
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### 自动化测试

**GitHub Actions** 会在以下情况自动运行测试：
- 创建 Pull Request 时
- 推送到 master/main 分支时

测试包括：
- ✅ 单元测试（8个测试）
- ✅ 集成测试（11个测试）
- ✅ 代码覆盖率报告

## 🐛 常见问题

### Q: sxtwl 安装失败

`sxtwl` 包需要 C++ 编译环境，在 Windows 上安装会失败。

**解决方案**:
- 罗喉功能为可选功能，不影响八字和生肖功能
- 如需使用罗喉功能，需在 Linux 环境（如 Lambda）中编译
- requirements.txt 中已注释掉 sxtwl，不会影响部署

### Q: 如何运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 只运行单元测试
python -m pytest tests/unit -v

# 只运行集成测试  
python -m pytest tests/integration -v

# 查看覆盖率
python -m pytest tests/ --cov=app
```

### Q: 导入错误 ModuleNotFoundError

确保依赖已安装:
```bash
pip install -r requirements.txt -t layer/python
```

### Q: 配置文件找不到

确保已创建 `config.toml`:
```bash
cp config.toml.example config.toml
# 然后编辑填入你的 AWS 信息
```

### Q: GitHub Actions 失败

检查 Secrets 是否正确设置:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`

### Q: Lambda 超时

增加超时时间:
```bash
aws lambda update-function-configuration \
  --function-name bazi-microservice \
  --timeout 60
```

### Q: 权限错误

确保 IAM 用户有以下权限:
- `AWSLambdaFullAccess`
- `IAMFullAccess`
- `AmazonAPIGatewayAdministrator`

## 🎯 快速命令参考

```bash
# 部署
./scripts/auto_deploy.sh

# 测试
curl https://API端点/health

# 查看日志
aws logs tail /aws/lambda/bazi-microservice --follow

# 更新
git push origin master

# 获取 API 端点
aws lambda get-function --function-name bazi-microservice \
  --query 'Configuration.FunctionArn'
```
