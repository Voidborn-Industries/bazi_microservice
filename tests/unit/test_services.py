#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单元测试 - 测试各个服务类的功能
Unit Tests - Test individual service classes
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import BaziService, ShengxiaoService


class TestBaziService(unittest.TestCase):
    """测试八字服务"""

    def test_calculate_bazi_gregorian(self):
        """测试八字计算 - 公历"""
        result = BaziService.calculate_bazi(
            year=1990,
            month=5,
            day=15,
            hour=14,
            is_gregorian=True,
            is_leap=False,
            is_female=False
        )

        self.assertIsNotNone(result)
        self.assertIn('bazi', result)
        self.assertIn('solar', result)
        self.assertIn('lunar', result)
        self.assertEqual(result['solar']['year'], 1990)
        self.assertEqual(result['solar']['month'], 5)
        self.assertEqual(result['solar']['day'], 15)

    def test_calculate_bazi_lunar(self):
        """测试八字计算 - 农历"""
        result = BaziService.calculate_bazi(
            year=2020,
            month=1,
            day=1,
            hour=12,
            is_gregorian=False,
            is_leap=False,
            is_female=True
        )

        self.assertIsNotNone(result)
        self.assertIn('bazi', result)
        self.assertIn('full', result['bazi'])
        self.assertTrue(len(result['bazi']['full']) > 0)

    def test_calculate_bazi_female(self):
        """测试八字计算 - 女性"""
        result = BaziService.calculate_bazi(
            year=1995,
            month=3,
            day=20,
            hour=8,
            is_gregorian=True,
            is_leap=False,
            is_female=True
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['input']['isFemale'], True)
        self.assertIn('fortune', result)

    def test_bazi_structure(self):
        """测试八字返回结构完整性"""
        result = BaziService.calculate_bazi(1990, 5, 15, 14, True)

        # 检查必需字段
        self.assertIn('input', result)
        self.assertIn('solar', result)
        self.assertIn('lunar', result)
        self.assertIn('bazi', result)
        self.assertIn('fortune', result)
        self.assertIn('zodiac', result)

        # 检查八字结构
        bazi = result['bazi']
        for pillar in ['year', 'month', 'day', 'time']:
            self.assertIn(pillar, bazi)
            self.assertIn('pillar', bazi[pillar])
            self.assertIn('gan', bazi[pillar])
            self.assertIn('zhi', bazi[pillar])


class TestShengxiaoService(unittest.TestCase):
    """测试生肖服务"""

    def test_get_compatibility_tiger(self):
        """测试生肖兼容性 - 虎"""
        result = ShengxiaoService.get_compatibility('虎')

        self.assertIsNotNone(result)
        self.assertEqual(result['zodiac'], '虎')
        self.assertEqual(result['zhi'], '寅')
        self.assertIn('compatible', result)
        self.assertIn('incompatible', result)

    def test_get_compatibility_dragon(self):
        """测试生肖兼容性 - 龙"""
        result = ShengxiaoService.get_compatibility('龙')

        self.assertIsNotNone(result)
        self.assertEqual(result['zodiac'], '龙')
        self.assertIn('compatible', result)

    def test_invalid_zodiac(self):
        """测试无效生肖"""
        with self.assertRaises(ValueError) as context:
            ShengxiaoService.get_compatibility('invalid')

        self.assertIn('Invalid zodiac', str(context.exception))

    def test_all_zodiacs(self):
        """测试所有12生肖"""
        zodiacs = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']

        for zodiac in zodiacs:
            result = ShengxiaoService.get_compatibility(zodiac)
            self.assertEqual(result['zodiac'], zodiac)
            self.assertIn('compatible', result)
            self.assertIn('incompatible', result)


if __name__ == '__main__':
    unittest.main()
