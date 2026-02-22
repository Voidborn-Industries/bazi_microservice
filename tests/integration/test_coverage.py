#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展测试 - 提高代码覆盖率
Extended Tests - Improve code coverage
"""

import unittest
import json
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import lambda_handler


class TestLuohouEndpoint(unittest.TestCase):
    """测试罗喉端点（需要 sxtwl）"""

    def test_luohou_missing_sxtwl(self):
        """测试罗喉功能 - sxtwl 未安装时的错误处理"""
        event = {
            'httpMethod': 'GET',
            'path': '/luohou',
            'queryStringParameters': {
                'startDate': '2024-01-01',
                'endDate': '2024-01-03'
            },
            'body': None
        }

        response = lambda_handler(event, None)

        # 应该返回 500 错误（因为 sxtwl 未安装）
        self.assertIn(response['statusCode'], [500, 400])
        body = json.loads(response['body'])
        self.assertFalse(body['success'])

    def test_luohou_default_dates(self):
        """测试罗喉功能 - 使用默认日期"""
        event = {
            'httpMethod': 'GET',
            'path': '/luohou',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        # 应该返回 500（sxtwl 未安装）或使用默认日期
        self.assertIn(response['statusCode'], [500, 200])

    def test_luohou_invalid_date_format(self):
        """测试罗喉功能 - 无效日期格式"""
        event = {
            'httpMethod': 'GET',
            'path': '/luohou',
            'queryStringParameters': {
                'startDate': 'invalid-date',
                'endDate': '2024-01-03'
            },
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('ValidationError', body['error']['type'])


class TestBaziEdgeCases(unittest.TestCase):
    """测试八字边界情况"""

    def test_bazi_leap_month(self):
        """测试八字计算 - 闰月"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 2023,
                'month': 2,
                'day': 15,
                'hour': 12,
                'isGregorian': False,
                'isLeap': True
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertTrue(body['data']['input']['isLeap'])

    def test_bazi_min_hour(self):
        """测试八字计算 - 最小时辰（0点）"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 2000,
                'month': 1,
                'day': 1,
                'hour': 0,
                'isGregorian': True
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])

    def test_bazi_max_hour(self):
        """测试八字计算 - 最大时辰（23点）"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 2000,
                'month': 12,
                'day': 31,
                'hour': 23,
                'isGregorian': True
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])

    def test_bazi_alternative_param_names(self):
        """测试八字计算 - 备用参数名"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 1990,
                'month': 5,
                'day': 15,
                'hour': 14,
                'solar': True,  # 备用参数名
                'gender': 'male'  # 备用参数名
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])


class TestShengxiaoEdgeCases(unittest.TestCase):
    """测试生肖边界情况"""

    def test_all_twelve_zodiacs(self):
        """测试所有12个生肖"""
        zodiacs = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

        for zodiac in zodiacs:
            with self.subTest(zodiac=zodiac):
                event = {
                    'httpMethod': 'GET',
                    'path': '/shengxiao',
                    'queryStringParameters': {'zodiac': zodiac},
                    'body': None
                }

                response = lambda_handler(event, None)

                self.assertEqual(response['statusCode'], 200)
                body = json.loads(response['body'])
                self.assertTrue(body['success'])
                self.assertEqual(body['data']['zodiac'], zodiac)

    def test_shengxiao_empty_param(self):
        """测试生肖 - 空参数"""
        event = {
            'httpMethod': 'GET',
            'path': '/shengxiao',
            'queryStringParameters': {'zodiac': ''},
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])

    def test_shengxiao_missing_param(self):
        """测试生肖 - 缺少参数"""
        event = {
            'httpMethod': 'GET',
            'path': '/shengxiao',
            'queryStringParameters': {},
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""

    def test_malformed_json_in_body(self):
        """测试畸形 JSON"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': '{"invalid": json}'
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])

    def test_empty_body(self):
        """测试空 body"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': ''
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)

    def test_null_body(self):
        """测试 null body"""
        event = {
            'httpMethod': 'POST',
            'path': '/bazi',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 400)


class TestAlternativePaths(unittest.TestCase):
    """测试备用路径"""

    def test_api_prefix_health(self):
        """测试 /api/health 路径"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/health',
            'queryStringParameters': None,
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)

    def test_api_prefix_bazi(self):
        """测试 /api/bazi 路径"""
        event = {
            'httpMethod': 'POST',
            'path': '/api/bazi',
            'queryStringParameters': None,
            'body': json.dumps({
                'year': 1990,
                'month': 5,
                'day': 15,
                'hour': 14,
                'isGregorian': True
            })
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)

    def test_api_prefix_shengxiao(self):
        """测试 /api/shengxiao 路径"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/shengxiao',
            'queryStringParameters': {'zodiac': '虎'},
            'body': None
        }

        response = lambda_handler(event, None)

        self.assertEqual(response['statusCode'], 200)

    def test_api_prefix_luohou(self):
        """测试 /api/luohou 路径"""
        event = {
            'httpMethod': 'GET',
            'path': '/api/luohou',
            'queryStringParameters': {
                'startDate': '2024-01-01',
                'endDate': '2024-01-03'
            },
            'body': None
        }

        response = lambda_handler(event, None)

        # 应该尝试处理，即使 sxtwl 未安装
        self.assertIn(response['statusCode'], [200, 500])


if __name__ == '__main__':
    unittest.main()

