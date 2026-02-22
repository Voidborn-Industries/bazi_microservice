#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成测试 - 测试完整的 Lambda handler API
Integration Tests - Test complete Lambda handler API
"""

import unittest
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import lambda_handler


class TestLambdaHandler(unittest.TestCase):
    """测试 Lambda Handler 集成"""

    def test_health_check(self):
        """测试健康检查端点"""
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'healthy')
        self.assertEqual(body['service'], 'bazi-microservice')

    def test_cors_preflight(self):
        """测试 CORS 预检请求"""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')

    def test_bazi_post_request(self):
        """测试八字计算 POST 请求"""
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

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertIn('data', body)
        self.assertIn('bazi', body['data'])

    def test_bazi_get_request(self):
        """测试八字计算 GET 请求（查询参数）"""
        event = {
            'httpMethod': 'GET',
            'path': '/bazi',
            'queryStringParameters': {
                'year': '1995',
                'month': '3',
                'day': '20',
                'hour': '8',
                'isGregorian': 'true'
            },
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])

    def test_shengxiao_request(self):
        """测试生肖合婚请求"""
        event = {
            'httpMethod': 'GET',
            'path': '/shengxiao',
            'queryStringParameters': {'zodiac': '虎'},
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['zodiac'], '虎')

    def test_missing_parameters(self):
        """测试缺少必需参数"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({'year': 1990})
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('error', body)

    def test_invalid_zodiac(self):
        """测试无效生肖"""
        event = {
            'httpMethod': 'GET',
            'path': '/shengxiao',
            'queryStringParameters': {'zodiac': 'invalid'},
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])

    def test_unknown_path(self):
        """测试未知路径"""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 404)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])

    def test_invalid_json(self):
        """测试无效 JSON"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': 'invalid json'
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])


class TestResponseFormat(unittest.TestCase):
    """测试响应格式"""

    def test_success_response_format(self):
        """测试成功响应格式"""
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        # 检查响应结构
        self.assertIn('statusCode', response)
        self.assertIn('headers', response)
        self.assertIn('body', response)

        # 检查 CORS 头
        headers = response['headers']
        self.assertIn('Access-Control-Allow-Origin', headers)
        self.assertIn('Content-Type', headers)

        # 检查 JSON 格式
        body = json.loads(response['body'])
        self.assertIsInstance(body, dict)

    def test_error_response_format(self):
        """测试错误响应格式"""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('error', body)
        self.assertIn('type', body['error'])
        self.assertIn('message', body['error'])
        self.assertIn('timestamp', body)


if __name__ == '__main__':
    unittest.main()

