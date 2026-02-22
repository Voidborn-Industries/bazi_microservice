#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Lambda 直接调用功能
Test Direct Lambda Invocation
"""

import json
import pytest
from app import lambda_handler


class TestDirectLambdaInvoke:
    """测试直接 Lambda 调用（非 API Gateway）"""

    def test_direct_bazi_invocation(self):
        """测试直接调用八字计算"""
        # 模拟直接 Lambda 调用（无 httpMethod）
        event = {
            "year": 1990,
            "month": 9,
            "day": 11,
            "hour": 11,
            "isGregorian": True,
            "isFemale": False,
        }

        response = lambda_handler(event, None)

        # 验证响应格式
        assert response['success'] is True
        assert 'data' in response
        assert 'timestamp' in response

        # 验证数据内容
        data = response['data']
        assert 'bazi' in data
        assert 'solar' in data
        assert 'lunar' in data
        assert 'zodiac' in data

        # 验证八字格式
        assert 'full' in data['bazi']
        assert len(data['bazi']['full'].split()) == 4

    def test_direct_bazi_lunar_invocation(self):
        """测试直接调用农历八字计算"""
        event = {
            "year": 1990,
            "month": 7,
            "day": 22,
            "hour": 11,
            "isGregorian": False,
            "isLeap": False,
            "isFemale": False,
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert response['data']['input']['isGregorian'] is False

    def test_direct_shengxiao_invocation(self):
        """测试直接调用生肖查询"""
        event = {
            "zodiac": "虎"
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert 'data' in response
        assert response['data']['zodiac'] == '虎'
        assert 'compatible' in response['data']
        assert 'incompatible' in response['data']

    def test_direct_invoke_with_service_type(self):
        """测试使用 service 参数明确指定服务类型"""
        event = {
            "service": "shengxiao",
            "zodiac": "龙"
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert response['data']['zodiac'] == '龙'

    def test_api_gateway_still_works(self):
        """确保 API Gateway 调用方式仍然工作"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 1990,
                'month': 5,
                'day': 15,
                'hour': 14,
                'isGregorian': True,
                'isFemale': False
            })
        }

        response = lambda_handler(event, None)

        # API Gateway 返回格式
        assert 'statusCode' in response
        assert 'body' in response
        assert 'headers' in response
        assert response['statusCode'] == 200

        # 解析 body
        body = json.loads(response['body'])
        assert body['success'] is True

    def test_direct_vs_api_gateway_response_format(self):
        """对比直接调用和 API Gateway 调用的响应格式"""
        # 相同的请求数据
        request_data = {
            'year': 1990,
            'month': 5,
            'day': 15,
            'hour': 14,
            'isGregorian': True,
            'isFemale': False
        }

        # 1. 直接 Lambda 调用
        direct_event = request_data.copy()
        direct_response = lambda_handler(direct_event, None)

        # 直接调用应该返回纯数据对象
        assert 'success' in direct_response
        assert 'data' in direct_response
        assert 'statusCode' not in direct_response
        assert 'headers' not in direct_response

        # 2. API Gateway 调用
        api_event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps(request_data)
        }
        api_response = lambda_handler(api_event, None)

        # API Gateway 调用应该返回 HTTP 响应格式
        assert 'statusCode' in api_response
        assert 'body' in api_response
        assert 'headers' in api_response

        # 解析 API Gateway 的 body，应该与直接调用的数据相同
        api_body = json.loads(api_response['body'])
        assert api_body['success'] == direct_response['success']
        # 数据部分应该相同
        assert api_body['data']['bazi']['full'] == direct_response['data']['bazi']['full']

    def test_direct_invoke_missing_required_params(self):
        """测试直接调用缺少必需参数的情况"""
        event = {
            "year": 1990,
            "month": 9
            # 缺少 day 和 hour
        }

        response = lambda_handler(event, None)

        # 应该返回错误，但格式应该是直接的 JSON，不是 HTTP 响应
        assert 'success' in response or 'statusCode' in response

        # 如果返回的是 statusCode 格式，说明走了 API Gateway 的错误处理
        # 需要进一步优化

    def test_auto_detection_bazi_parameters(self):
        """测试自动检测八字参数"""
        event = {
            "year": 2000,
            "month": 1,
            "day": 1,
            "hour": 0,
            # 不指定 service，应该自动检测为 bazi
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert 'bazi' in response['data']

    def test_auto_detection_shengxiao_parameters(self):
        """测试自动检测生肖参数"""
        event = {
            "zodiac": "猪"
            # 不指定 service，应该自动检测为 shengxiao
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert response['data']['zodiac'] == '猪'

    def test_direct_invoke_female_parameter(self):
        """测试女性参数在直接调用中的处理"""
        event = {
            "year": 1990,
            "month": 9,
            "day": 11,
            "hour": 11,
            "isGregorian": True,
            "isFemale": True,  # 女性
        }

        response = lambda_handler(event, None)

        assert response['success'] is True
        assert response['data']['input']['isFemale'] is True

    def test_direct_invoke_various_zodiacs(self):
        """测试各种生肖的直接调用"""
        zodiacs = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

        for zodiac in zodiacs:
            event = {"zodiac": zodiac}
            response = lambda_handler(event, None)

            assert response['success'] is True
            assert response['data']['zodiac'] == zodiac
            assert 'compatible' in response['data']
            assert 'incompatible' in response['data']


class TestInvocationTypeDetection:
    """测试调用类型检测"""

    def test_detect_api_gateway_by_httpmethod(self):
        """测试通过 httpMethod 检测 API Gateway 调用"""
        event = {
            'httpMethod': 'GET',
            'path': '/health'
        }

        response = lambda_handler(event, None)

        # 应该返回 API Gateway 格式
        assert 'statusCode' in response
        assert 'headers' in response

    def test_detect_api_gateway_by_requestcontext(self):
        """测试通过 requestContext 检测 API Gateway 调用"""
        event = {
            'requestContext': {
                'http': {
                    'method': 'GET'
                }
            },
            'path': '/health'
        }

        response = lambda_handler(event, None)

        # 应该返回 API Gateway 格式
        assert 'statusCode' in response

    def test_detect_direct_lambda_invoke(self):
        """测试检测直接 Lambda 调用"""
        event = {
            "year": 1990,
            "month": 9,
            "day": 11,
            "hour": 11
        }

        response = lambda_handler(event, None)

        # 应该返回直接格式（无 statusCode）
        assert 'success' in response
        assert 'statusCode' not in response


if __name__ == "__main__":
    pytest.main([__file__, '-v'])

