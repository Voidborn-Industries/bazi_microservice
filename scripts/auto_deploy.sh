#!/bin/bash
################################################################################
# 八字微服务自动部署脚本
# Bazi Microservice Auto Deploy Script
################################################################################

set -e  # 遇到错误立即退出
set -o pipefail  # 管道命令失败时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 获取脚本所在目录和项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 读取配置文件
CONFIG_FILE="$PROJECT_ROOT/config.toml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}错误: 找不到配置文件 config.toml${NC}"
    echo -e "${YELLOW}请复制 config.toml.example 为 config.toml 并填入你的 AWS 信息${NC}"
    exit 1
fi

# 使用 Python 读取 TOML 配置
read_config() {
    python3 -c "
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print('请安装 tomli: pip install tomli', file=sys.stderr)
        sys.exit(1)

with open('$CONFIG_FILE', 'rb') as f:
    config = tomllib.load(f)
    print(config['$1']['$2'])
"
}

# 读取配置
AWS_ACCESS_KEY_ID=$(read_config aws access_key_id)
AWS_SECRET_ACCESS_KEY=$(read_config aws secret_access_key)
REGION=$(read_config aws region)
FUNCTION_NAME=$(read_config lambda function_name)
LAYER_NAME=$(read_config lambda layer_name)
MEMORY_SIZE=$(read_config lambda memory_size)
TIMEOUT=$(read_config lambda timeout)

# 导出 AWS 环境变量
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=$REGION

PYTHON_VERSION="python3.14"

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo ""
    echo "================================================================================"
    print_message "$CYAN" "$1"
    echo "================================================================================"
}

print_success() {
    print_message "$GREEN" "✓ $1"
}

print_error() {
    print_message "$RED" "✗ $1"
}

print_warning() {
    print_message "$YELLOW" "⚠ $1"
}

print_info() {
    print_message "$BLUE" "ℹ $1"
}

# 检查必需的工具
check_requirements() {
    print_header "检查环境要求 Checking Requirements"

    local missing_tools=()

    # 检查 AWS CLI
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws-cli")
    else
        print_success "AWS CLI: $(aws --version)"
    fi

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    else
        print_success "Python: $(python3 --version)"
    fi

    # 检查 pip
    if ! command -v pip3 &> /dev/null; then
        missing_tools+=("pip3")
    else
        print_success "pip: $(pip3 --version)"
    fi

    # 检查 zip
    if ! command -v zip &> /dev/null; then
        missing_tools+=("zip")
    else
        print_success "zip 命令已安装"
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "缺少以下工具: ${missing_tools[*]}"
        exit 1
    fi

    # 检查 AWS 凭证
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS 凭证未配置或无效"
        print_info "请运行: aws configure"
        exit 1
    fi

    local aws_identity=$(aws sts get-caller-identity --query 'Account' --output text)
    print_success "AWS Account: $aws_identity"
    print_success "AWS Region: $REGION"
}

# 清理旧文件
clean_build() {
    print_header "清理构建目录 Cleaning Build Directory"

    cd "$PROJECT_ROOT"

    if [ -d "build" ]; then
        rm -rf build
        print_success "已删除 build 目录"
    fi

    if [ -d "layer" ]; then
        rm -rf layer
        print_success "已删除 layer 目录"
    fi

    if [ -f "bazi-lambda.zip" ]; then
        rm -f bazi-lambda.zip
        print_success "已删除旧的 ZIP 文件"
    fi

    if [ -f "layer.zip" ]; then
        rm -f layer.zip
        print_success "已删除旧的 Layer ZIP"
    fi
}

# 创建 Lambda Layer (包含依赖)
create_layer() {
    print_header "创建 Lambda Layer Creating Lambda Layer"

    cd "$PROJECT_ROOT"

    # 创建 layer 目录
    mkdir -p layer/python
    print_info "创建 layer/python 目录"

    # 安装依赖到 layer
    print_info "安装 Python 依赖到 Layer..."
    pip3 install -r requirements.txt -t layer/python --quiet --upgrade

    if [ $? -eq 0 ]; then
        print_success "依赖安装成功"
    else
        print_error "依赖安装失败"
        exit 1
    fi

    # 清理不必要的文件以减小包大小
    print_info "清理不必要的文件..."
    find layer/python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find layer/python -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find layer/python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
    find layer/python -name "*.pyc" -delete 2>/dev/null || true
    find layer/python -name "*.pyo" -delete 2>/dev/null || true
    find layer/python -name "*.so" -type f ! -name "*cpython*" -delete 2>/dev/null || true

    # 创建 Layer ZIP
    print_info "打包 Layer..."
    cd layer
    zip -r9 ../layer.zip . -q
    cd ..

    local layer_size=$(du -h layer.zip | cut -f1)
    print_success "Layer 打包完成: $layer_size"

    # 发布 Layer
    print_info "发布 Lambda Layer..."

    local layer_arn=$(aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --description "Bazi microservice dependencies (bidict, lunar_python, colorama)" \
        --compatible-runtimes "$PYTHON_VERSION" \
        --zip-file fileb://layer.zip \
        --region "$REGION" \
        --query 'LayerVersionArn' \
        --output text 2>&1)

    if [ $? -eq 0 ]; then
        print_success "Layer 发布成功"
        print_info "Layer ARN: $layer_arn"
        echo "$layer_arn" > .layer_arn
    else
        print_error "Layer 发布失败: $layer_arn"
        exit 1
    fi
}

# 构建应用包
build_package() {
    print_header "构建应用包 Building Application Package"

    cd "$PROJECT_ROOT"

    # 创建 build 目录
    mkdir -p build

    # 复制 Python 源文件
    print_info "复制源代码文件..."
    local python_files=(
        "app.py"
        "bazi.py"
        "common.py"
        "convert.py"
        "datas.py"
        "ganzhi.py"
        "luohou.py"
        "shengxiao.py"
        "sizi.py"
        "yue.py"
    )

    for file in "${python_files[@]}"; do
        if [ -f "$file" ]; then
            cp "$file" build/
            print_success "复制 $file"
        else
            print_warning "文件不存在: $file"
        fi
    done

    # 创建部署 ZIP
    print_info "创建部署包..."
    cd build
    zip -r9 ../bazi-lambda.zip . -q
    cd ..

    local package_size=$(du -h bazi-lambda.zip | cut -f1)
    print_success "应用包创建完成: $package_size"
}

# 检查 Lambda 函数是否存在
function_exists() {
    aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$REGION" \
        &> /dev/null
    return $?
}

# 创建或更新 Lambda 函数
deploy_lambda() {
    print_header "部署 Lambda 函数 Deploying Lambda Function"

    cd "$PROJECT_ROOT"

    # 读取 Layer ARN
    local layer_arn=""
    if [ -f ".layer_arn" ]; then
        layer_arn=$(cat .layer_arn)
    fi

    if function_exists; then
        print_info "更新现有 Lambda 函数..."

        # 更新函数代码
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file fileb://bazi-lambda.zip \
            --region "$REGION" \
            --output text > /dev/null

        if [ $? -eq 0 ]; then
            print_success "函数代码更新成功"
        else
            print_error "函数代码更新失败"
            exit 1
        fi

        # 等待更新完成
        print_info "等待函数更新完成..."
        aws lambda wait function-updated \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION"

        # 更新函数配置
        if [ ! -z "$layer_arn" ]; then
            aws lambda update-function-configuration \
                --function-name "$FUNCTION_NAME" \
                --layers "$layer_arn" \
                --timeout $TIMEOUT \
                --memory-size $MEMORY_SIZE \
                --region "$REGION" \
                --output text > /dev/null

            print_success "函数配置更新成功 (包含 Layer)"
        fi

    else
        print_info "创建新的 Lambda 函数..."

        # 创建 IAM 角色 (如果不存在)
        create_lambda_role

        # 等待角色生效
        sleep 10

        local role_arn=$(aws iam get-role \
            --role-name "${FUNCTION_NAME}-role" \
            --query 'Role.Arn' \
            --output text)

        # 创建函数
        local layer_param=""
        if [ ! -z "$layer_arn" ]; then
            layer_param="--layers $layer_arn"
        fi

        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime "$PYTHON_VERSION" \
            --role "$role_arn" \
            --handler "app.lambda_handler" \
            --zip-file fileb://bazi-lambda.zip \
            --timeout $TIMEOUT \
            --memory-size $MEMORY_SIZE \
            --description "Bazi Chinese fortune-telling microservice" \
            $layer_param \
            --region "$REGION" \
            --output text > /dev/null

        if [ $? -eq 0 ]; then
            print_success "Lambda 函数创建成功"
        else
            print_error "Lambda 函数创建失败"
            exit 1
        fi
    fi

    # 获取函数 ARN
    local function_arn=$(aws lambda get-function \
        --function-name "$FUNCTION_NAME" \
        --region "$REGION" \
        --query 'Configuration.FunctionArn' \
        --output text)

    print_info "Function ARN: $function_arn"
}

# 创建 Lambda IAM 角色
create_lambda_role() {
    local role_name="${FUNCTION_NAME}-role"

    # 检查角色是否存在
    if aws iam get-role --role-name "$role_name" &> /dev/null; then
        print_info "IAM 角色已存在: $role_name"
        return 0
    fi

    print_info "创建 IAM 角色: $role_name"

    # 创建信任策略
    local trust_policy='{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Service": "lambda.amazonaws.com"
          },
          "Action": "sts:AssumeRole"
        }
      ]
    }'

    # 创建角色
    aws iam create-role \
        --role-name "$role_name" \
        --assume-role-policy-document "$trust_policy" \
        --description "Bazi microservice Lambda execution role" \
        --output text > /dev/null

    # 附加基本执行策略
    aws iam attach-role-policy \
        --role-name "$role_name" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

    print_success "IAM 角色创建成功"
}

# 创建或更新 API Gateway
deploy_api_gateway() {
    print_header "配置 API Gateway Configuring API Gateway"

    # 检查 API 是否存在
    local api_id=$(aws apigatewayv2 get-apis \
        --query "Items[?Name=='bazi-api'].ApiId" \
        --output text \
        --region "$REGION")

    if [ -z "$api_id" ]; then
        print_info "创建新的 HTTP API..."

        local function_arn=$(aws lambda get-function \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" \
            --query 'Configuration.FunctionArn' \
            --output text)

        api_id=$(aws apigatewayv2 create-api \
            --name "bazi-api" \
            --protocol-type HTTP \
            --description "Bazi microservice HTTP API" \
            --cors-configuration "AllowOrigins=*,AllowMethods=*,AllowHeaders=*" \
            --query 'ApiId' \
            --output text \
            --region "$REGION")

        if [ $? -eq 0 ]; then
            print_success "API 创建成功: $api_id"
        else
            print_error "API 创建失败"
            exit 1
        fi

        # 创建集成
        print_info "创建 Lambda 集成..."
        local integration_id=$(aws apigatewayv2 create-integration \
            --api-id "$api_id" \
            --integration-type AWS_PROXY \
            --integration-uri "$function_arn" \
            --payload-format-version 2.0 \
            --query 'IntegrationId' \
            --output text \
            --region "$REGION")

        # 创建路由
        print_info "创建 API 路由..."
        local routes=(
            "GET /health"
            "GET /api/health"
            "POST /bazi"
            "POST /api/bazi"
            "GET /bazi"
            "GET /shengxiao"
            "GET /api/shengxiao"
            "GET /luohou"
            "GET /api/luohou"
            "OPTIONS /{proxy+}"
        )

        for route in "${routes[@]}"; do
            aws apigatewayv2 create-route \
                --api-id "$api_id" \
                --route-key "$route" \
                --target "integrations/$integration_id" \
                --region "$REGION" \
                --output text > /dev/null

            print_success "创建路由: $route"
        done

        # 授予 API Gateway 调用权限
        print_info "授予 API Gateway 调用权限..."
        local account_id=$(aws sts get-caller-identity --query 'Account' --output text)
        local source_arn="arn:aws:execute-api:${REGION}:${account_id}:${api_id}/*/*"

        aws lambda add-permission \
            --function-name "$FUNCTION_NAME" \
            --statement-id "apigateway-invoke-$(date +%s)" \
            --action lambda:InvokeFunction \
            --principal apigateway.amazonaws.com \
            --source-arn "$source_arn" \
            --region "$REGION" \
            --output text > /dev/null 2>&1 || true

        print_success "权限配置完成"

    else
        print_info "使用现有 API: $api_id"
    fi

    # 获取 API 端点
    local api_endpoint="https://${api_id}.execute-api.${REGION}.amazonaws.com"

    print_success "API Gateway 配置完成"
    print_info "API 端点: $api_endpoint"

    echo "$api_endpoint" > .api_endpoint
}

# 测试部署
test_deployment() {
    print_header "测试部署 Testing Deployment"

    if [ ! -f ".api_endpoint" ]; then
        print_warning "未找到 API 端点，跳过测试"
        return 0
    fi

    local api_endpoint=$(cat .api_endpoint)

    # 测试健康检查
    print_info "测试健康检查端点..."
    local health_response=$(curl -s "${api_endpoint}/health")

    if echo "$health_response" | grep -q "healthy"; then
        print_success "健康检查通过"
        echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"
    else
        print_warning "健康检查响应异常"
        echo "$health_response"
    fi
}

# 显示部署摘要
show_summary() {
    print_header "部署摘要 Deployment Summary"

    print_success "部署完成! Deployment Completed!"
    echo ""

    if [ -f ".api_endpoint" ]; then
        local api_endpoint=$(cat .api_endpoint)

        print_info "API 端点 API Endpoints:"
        echo "  健康检查:     $api_endpoint/health"
        echo "  八字计算:     $api_endpoint/bazi"
        echo "  生肖合婚:     $api_endpoint/shengxiao"
        echo "  罗喉日时:     $api_endpoint/luohou"
        echo ""

        print_info "测试命令 Test Commands:"
        echo "  健康检查:"
        echo "    curl $api_endpoint/health"
        echo ""
        echo "  八字计算:"
        echo "    curl -X POST $api_endpoint/bazi \\"
        echo "      -H 'Content-Type: application/json' \\"
        echo "      -d '{\"year\":1990,\"month\":5,\"day\":15,\"hour\":14,\"isGregorian\":true}'"
        echo ""
        echo "  生肖合婚:"
        echo "    curl '$api_endpoint/shengxiao?zodiac=虎'"
        echo ""
    fi

    print_info "CloudWatch 日志:"
    echo "  aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
    echo ""

    print_info "更新函数:"
    echo "  ./scripts/auto_deploy.sh"
    echo ""
}

# 主函数
main() {
    print_header "八字微服务自动部署 Bazi Microservice Auto Deploy"
    print_info "区域: $REGION"
    print_info "函数名称: $FUNCTION_NAME"
    echo ""

    # 执行部署步骤
    check_requirements
    clean_build
    create_layer
    build_package
    deploy_lambda
    deploy_api_gateway
    test_deployment
    show_summary

    print_success "所有步骤完成! All steps completed!"
}

# 运行主函数
main "$@"





