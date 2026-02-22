#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字微服务 AWS Lambda 处理器
Bazi Microservice AWS Lambda Handler

提供中国传统命理计算服务的 REST API 端点
Provides REST API endpoints for Chinese fortune-telling services

Python 版本: 3.14+
作者: 资深工程师团队
Author: Senior Engineering Team
"""

import json
import traceback
import logging
from datetime import datetime, UTC
from io import StringIO
import sys
import os

# Configure logging for AWS Lambda CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import local modules
try:
    from lunar_python import Lunar, Solar
    from datas import shengxiaos, zhi_atts
    import collections
    logger.info("Successfully imported required modules")
except Exception as e:
    logger.error(f"Failed to import modules: {str(e)}")
    raise


class BaziService:
    """Service class for Bazi calculations"""

    @staticmethod
    def calculate_bazi(year, month, day, hour, is_gregorian=False, is_leap=False, is_female=False):
        """
        Calculate Bazi (八字) for given date/time

        Args:
            year: Year (int)
            month: Month (int)
            day: Day (int)
            hour: Hour (int)
            is_gregorian: Whether input is Gregorian calendar (bool)
            is_leap: Whether it's a leap month (bool, only for lunar calendar)
            is_female: Whether the person is female (bool)

        Returns:
            dict: Bazi calculation results
        """
        logger.info(f"[BAZI] Calculating for: {year}-{month}-{day} {hour}:00, gregorian={is_gregorian}, leap={is_leap}, female={is_female}")

        try:
            # Convert dates
            if is_gregorian:
                solar = Solar.fromYmdHms(int(year), int(month), int(day), int(hour), 0, 0)
                lunar = solar.getLunar()
                logger.info(f"[BAZI] Converted Gregorian to Lunar: {lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}")
            else:
                month_ = int(month) * -1 if is_leap else int(month)
                lunar = Lunar.fromYmdHms(int(year), month_, int(day), int(hour), 0, 0)
                solar = lunar.getSolar()
                logger.info(f"[BAZI] Using Lunar date, converted to Solar: {solar.getYear()}-{solar.getMonth()}-{solar.getDay()}")

            # Get eight characters
            ba = lunar.getEightChar()

            # Extract pillars
            year_pillar = ba.getYearGan() + ba.getYearZhi()
            month_pillar = ba.getMonthGan() + ba.getMonthZhi()
            day_pillar = ba.getDayGan() + ba.getDayZhi()
            time_pillar = ba.getTimeGan() + ba.getTimeZhi()

            logger.info(f"[BAZI] Eight characters: {year_pillar} {month_pillar} {day_pillar} {time_pillar}")

            # Get Nayin (纳音)
            year_nayin = ba.getYearNaYin()
            month_nayin = ba.getMonthNaYin()
            day_nayin = ba.getDayNaYin()
            time_nayin = ba.getTimeNaYin()

            # Get Shishen (十神)
            year_shishen = ba.getYearShiShenGan()
            month_shishen = ba.getMonthShiShenGan()
            day_shishen = "日主"
            time_shishen = ba.getTimeShiShenGan()

            # Get fortune cycles
            yun = ba.getYun(0 if is_female else 1)
            start_year = yun.getStartYear()
            start_month = yun.getStartMonth()
            start_day = yun.getStartDay()

            logger.info(f"[BAZI] Fortune starts at: {start_year}年{start_month}月{start_day}日")

            # Get 10-year cycles (大运)
            dayun_list = []
            dayuns = yun.getDaYun()
            for i in range(min(10, len(dayuns))):  # Get up to 10 cycles
                dayun = dayuns[i]
                gan = dayun.getGanZhi()[0:1]
                zhi = dayun.getGanZhi()[1:2]
                start_year_dayun = dayun.getStartYear()
                start_age = dayun.getStartAge()

                dayun_list.append({
                    "index": i,
                    "ganZhi": gan + zhi,
                    "gan": gan,
                    "zhi": zhi,
                    "startYear": start_year_dayun,
                    "startAge": start_age
                })

            logger.info(f"[BAZI] Generated {len(dayun_list)} Dayun cycles")

            result = {
                "input": {
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "isGregorian": is_gregorian,
                    "isLeap": is_leap,
                    "isFemale": is_female
                },
                "solar": {
                    "year": solar.getYear(),
                    "month": solar.getMonth(),
                    "day": solar.getDay(),
                    "formatted": f"{solar.getYear()}年{solar.getMonth()}月{solar.getDay()}日"
                },
                "lunar": {
                    "year": lunar.getYear(),
                    "month": abs(lunar.getMonth()),
                    "day": lunar.getDay(),
                    "isLeap": lunar.getMonth() < 0,
                    "formatted": f"{lunar.getYearInChinese()}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
                },
                "bazi": {
                    "year": {
                        "pillar": year_pillar,
                        "gan": ba.getYearGan(),
                        "zhi": ba.getYearZhi(),
                        "nayin": year_nayin,
                        "shishen": year_shishen
                    },
                    "month": {
                        "pillar": month_pillar,
                        "gan": ba.getMonthGan(),
                        "zhi": ba.getMonthZhi(),
                        "nayin": month_nayin,
                        "shishen": month_shishen
                    },
                    "day": {
                        "pillar": day_pillar,
                        "gan": ba.getDayGan(),
                        "zhi": ba.getDayZhi(),
                        "nayin": day_nayin,
                        "shishen": day_shishen
                    },
                    "time": {
                        "pillar": time_pillar,
                        "gan": ba.getTimeGan(),
                        "zhi": ba.getTimeZhi(),
                        "nayin": time_nayin,
                        "shishen": time_shishen
                    },
                    "full": f"{year_pillar} {month_pillar} {day_pillar} {time_pillar}"
                },
                "fortune": {
                    "startYear": start_year,
                    "startMonth": start_month,
                    "startDay": start_day,
                    "dayun": dayun_list[:10]  # Return first 10 cycles
                },
                "zodiac": {
                    "year": lunar.getYearShengXiao(),
                    "day": lunar.getDayShengXiao(),
                    "month": lunar.getMonthShengXiao(),
                    "time": lunar.getTimeShengXiao()
                }
            }

            logger.info("[BAZI] Calculation completed successfully")
            return result

        except Exception as e:
            logger.error(f"[BAZI] Error in calculation: {str(e)}")
            logger.error(traceback.format_exc())
            raise


class ShengxiaoService:
    """Service class for Chinese Zodiac (生肖) compatibility"""

    @staticmethod
    def get_compatibility(zodiac_name):
        """
        Get zodiac compatibility information

        Args:
            zodiac_name: Chinese zodiac name (str)

        Returns:
            dict: Compatibility information
        """
        logger.info(f"[SHENGXIAO] Checking compatibility for: {zodiac_name}")

        try:
            if zodiac_name not in shengxiaos.inverse:
                valid_zodiacs = list(shengxiaos.inverse.keys())
                logger.warning(f"[SHENGXIAO] Invalid zodiac: {zodiac_name}. Valid: {valid_zodiacs}")
                raise ValueError(f"Invalid zodiac. Must be one of: {', '.join(valid_zodiacs)}")

            zhi = shengxiaos.inverse[zodiac_name]
            logger.info(f"[SHENGXIAO] Zodiac {zodiac_name} corresponds to Zhi: {zhi}")

            def get_zodiac_list(key):
                """Helper to get list of zodiacs for a relationship type"""
                return [shengxiaos[item] for item in zhi_atts[zhi].get(key, [])]

            result = {
                "zodiac": zodiac_name,
                "zhi": zhi,
                "compatible": {
                    "sanhe": get_zodiac_list('合'),      # 三合
                    "liuhe": get_zodiac_list('六'),      # 六合
                    "sanhui": get_zodiac_list('会')      # 三会
                },
                "incompatible": {
                    "chong": get_zodiac_list('冲'),      # 相冲
                    "xing": get_zodiac_list('刑'),       # 相刑
                    "beixing": get_zodiac_list('被刑'),  # 被刑
                    "hai": get_zodiac_list('害'),        # 相害
                    "po": get_zodiac_list('破')          # 相破
                },
                "note": "生肖合婚只是八字合婚的一小部分，完整分析需要看八字全盘"
            }

            logger.info(f"[SHENGXIAO] Compatibility check completed for: {zodiac_name}")
            return result

        except Exception as e:
            logger.error(f"[SHENGXIAO] Error in compatibility check: {str(e)}")
            logger.error(traceback.format_exc())
            raise


class LuohouService:
    """Service class for Luohou (罗喉) calculations"""

    @staticmethod
    def calculate_luohou_dates(start_date, end_date):
        """
        Calculate Luohou dates in a date range

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            list: List of Luohou dates with details
        """
        logger.info(f"[LUOHOU] Calculating dates from {start_date} to {end_date}")

        try:
            try:
                import sxtwl
            except ImportError:
                logger.error("[LUOHOU] sxtwl module not available")
                raise ImportError("sxtwl module is required for Luohou calculations. Please ensure it's installed in the Lambda environment.")

            from ganzhi import Gan, Zhi, zhi_time

            # Define shi_hous mapping (罗喉时辰)
            shi_hous = {
                '子': ['卯', '申'], '丑': ['辰', '巳'], '寅': ['巳', '午'],
                '卯': ['午', '未'], '辰': ['未', '申'], '巳': ['申', '酉'],
                '午': ['酉', '戌'], '未': ['戌', '亥'], '申': ['亥', '子'],
                '酉': ['子', '丑'], '戌': ['丑', '寅'], '亥': ['寅', '卯']
            }

            Gans = collections.namedtuple("Gans", "year month day")
            Zhis = collections.namedtuple("Zhis", "year month day")

            # Parse dates
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            logger.info(f"[LUOHOU] Date range parsed: {start_dt} to {end_dt}")

            results = []
            current_dt = start_dt

            while current_dt <= end_dt:
                cal_day = sxtwl.fromSolar(current_dt.year, current_dt.month, current_dt.day)
                lunar = Lunar.fromYmd(cal_day.getLunarYear(), cal_day.getLunarMonth(), cal_day.getLunarDay())

                yTG = cal_day.getYearGZ()
                mTG = cal_day.getMonthGZ()
                dTG = cal_day.getDayGZ()

                gans = Gans(year=Gan[yTG.tg], month=Gan[mTG.tg], day=Gan[dTG.tg])
                zhis = Zhis(year=Zhi[yTG.dz], month=Zhi[mTG.dz], day=Zhi[dTG.dz])

                day_zhi = zhis[2]
                luohou_times = shi_hous.get(day_zhi, [])

                date_info = {
                    "gregorian": current_dt.strftime('%Y-%m-%d'),
                    "lunar": {
                        "year": cal_day.getLunarYear(),
                        "month": cal_day.getLunarMonth(),
                        "day": cal_day.getLunarDay(),
                        "isLeap": cal_day.isLunarLeap(),
                        "formatted": f"{cal_day.getLunarYear()}年{cal_day.getLunarMonth()}月{cal_day.getLunarDay()}日"
                    },
                    "ganzhi": {
                        "year": gans.year + zhis.year,
                        "month": gans.month + zhis.month,
                        "day": gans.day + zhis.day
                    },
                    "luohouTimes": [
                        {
                            "zhi": time_zhi,
                            "timeRange": zhi_time.get(time_zhi, "未知")
                        }
                        for time_zhi in luohou_times
                    ]
                }

                results.append(date_info)

                # Move to next day
                from datetime import timedelta
                current_dt += timedelta(days=1)

            logger.info(f"[LUOHOU] Calculated {len(results)} days")
            return results

        except Exception as e:
            logger.error(f"[LUOHOU] Error in calculation: {str(e)}")
            logger.error(traceback.format_exc())
            raise


def create_response(status_code, body, headers=None):
    """
    Create standardized API response with CORS headers

    Args:
        status_code: HTTP status code (int)
        body: Response body (dict)
        headers: Additional headers (dict)

    Returns:
        dict: API Gateway response format
    """
    default_headers = {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

    if headers:
        default_headers.update(headers)

    response = {
        'statusCode': status_code,
        'headers': default_headers,
        'body': json.dumps(body, ensure_ascii=False, indent=2)
    }

    logger.info(f"[RESPONSE] Status: {status_code}, Body length: {len(response['body'])}")
    return response


def create_error_response(status_code, message, error_type="Error", details=None):
    """
    Create standardized error response

    Args:
        status_code: HTTP status code (int)
        message: Error message (str)
        error_type: Type of error (str)
        details: Additional error details (str)

    Returns:
        dict: Error response
    """
    logger.error(f"[ERROR] {error_type}: {message}")
    if details:
        logger.error(f"[ERROR] Details: {details}")

    body = {
        'success': False,
        'error': {
            'type': error_type,
            'message': message
        },
        'timestamp': datetime.now(UTC).isoformat()
    }

    if details:
        body['error']['details'] = details

    return create_response(status_code, body)


def validate_required_params(params, required_fields):
    """
    Validate required parameters

    Args:
        params: Parameters dict
        required_fields: List of required field names

    Returns:
        tuple: (is_valid, missing_fields)
    """
    missing = [field for field in required_fields if field not in params or params[field] is None]
    return len(missing) == 0, missing


def lambda_handler(event, context):
    """
    AWS Lambda handler function - main entry point

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        dict: API Gateway response
    """
    logger.info("="*80)
    logger.info("[LAMBDA] Handler invoked")
    logger.info(f"[LAMBDA] Event: {json.dumps(event)}")

    try:
        # Handle OPTIONS request for CORS preflight
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'POST'))

        if http_method == 'OPTIONS':
            logger.info("[LAMBDA] CORS preflight request")
            return create_response(200, {'message': 'OK'})

        # Extract path and parameters
        path = event.get('path', event.get('rawPath', '/'))
        logger.info(f"[LAMBDA] Path: {path}, Method: {http_method}")

        # Parse body if present
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
                logger.info(f"[LAMBDA] Parsed body: {json.dumps(body)}")
            except json.JSONDecodeError as e:
                logger.error(f"[LAMBDA] Invalid JSON in body: {str(e)}")
                return create_error_response(400, "Invalid JSON in request body", "JSONDecodeError")

        # Merge query parameters
        query_params = event.get('queryStringParameters') or {}
        params = {**query_params, **body}
        logger.info(f"[LAMBDA] Combined params: {json.dumps(params)}")

        # Route to appropriate service
        if path == '/bazi' or path == '/api/bazi':
            logger.info("[ROUTE] Routing to Bazi service")
            return handle_bazi_request(params)

        elif path == '/shengxiao' or path == '/api/shengxiao':
            logger.info("[ROUTE] Routing to Shengxiao service")
            return handle_shengxiao_request(params)

        elif path == '/luohou' or path == '/api/luohou':
            logger.info("[ROUTE] Routing to Luohou service")
            return handle_luohou_request(params)

        elif path == '/health' or path == '/api/health':
            logger.info("[ROUTE] Health check")
            return create_response(200, {
                'status': 'healthy',
                'service': 'bazi-microservice',
                'timestamp': datetime.now(UTC).isoformat(),
                'version': '1.0.0'
            })

        else:
            logger.warning(f"[ROUTE] Unknown path: {path}")
            return create_error_response(404, f"Path not found: {path}", "NotFound")

    except Exception as e:
        logger.error(f"[LAMBDA] Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(500, "Internal server error", "InternalError", str(e))


def handle_bazi_request(params):
    """
    Handle Bazi calculation request

    Args:
        params: Request parameters

    Returns:
        dict: API response
    """
    logger.info("[HANDLER] Processing Bazi request")

    try:
        # Validate required parameters
        required = ['year', 'month', 'day', 'hour']
        is_valid, missing = validate_required_params(params, required)

        if not is_valid:
            logger.warning(f"[HANDLER] Missing required parameters: {missing}")
            return create_error_response(400, f"Missing required parameters: {', '.join(missing)}", "ValidationError")

        # Parse and validate parameters
        try:
            year = int(params['year'])
            month = int(params['month'])
            day = int(params['day'])
            hour = int(params['hour'])

            # Validate ranges
            if not (1900 <= year <= 2100):
                raise ValueError("Year must be between 1900 and 2100")
            if not (1 <= month <= 12):
                raise ValueError("Month must be between 1 and 12")
            if not (1 <= day <= 31):
                raise ValueError("Day must be between 1 and 31")
            if not (0 <= hour <= 23):
                raise ValueError("Hour must be between 0 and 23")

        except ValueError as e:
            logger.warning(f"[HANDLER] Invalid parameter value: {str(e)}")
            return create_error_response(400, str(e), "ValidationError")

        # Parse optional boolean parameters
        is_gregorian = str(params.get('isGregorian', params.get('g', 'false'))).lower() in ('true', '1', 'yes')
        is_leap = str(params.get('isLeap', params.get('r', 'false'))).lower() in ('true', '1', 'yes')
        is_female = str(params.get('isFemale', params.get('n', 'false'))).lower() in ('true', '1', 'yes')

        logger.info(f"[HANDLER] Validated params: year={year}, month={month}, day={day}, hour={hour}")

        # Calculate Bazi
        result = BaziService.calculate_bazi(year, month, day, hour, is_gregorian, is_leap, is_female)

        response_body = {
            'success': True,
            'data': result,
            'timestamp': datetime.now(UTC).isoformat()
        }

        return create_response(200, response_body)

    except Exception as e:
        logger.error(f"[HANDLER] Error in Bazi handler: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(500, "Error calculating Bazi", "CalculationError", str(e))


def handle_shengxiao_request(params):
    """
    Handle Shengxiao compatibility request

    Args:
        params: Request parameters

    Returns:
        dict: API response
    """
    logger.info("[HANDLER] Processing Shengxiao request")

    try:
        # Validate required parameters
        zodiac = params.get('zodiac', params.get('shengxiao'))

        if not zodiac:
            logger.warning("[HANDLER] Missing zodiac parameter")
            return create_error_response(400, "Missing required parameter: zodiac", "ValidationError")

        logger.info(f"[HANDLER] Zodiac parameter: {zodiac}")

        # Get compatibility
        result = ShengxiaoService.get_compatibility(zodiac)

        response_body = {
            'success': True,
            'data': result,
            'timestamp': datetime.now(UTC).isoformat()
        }

        return create_response(200, response_body)

    except ValueError as e:
        logger.warning(f"[HANDLER] Validation error: {str(e)}")
        return create_error_response(400, str(e), "ValidationError")

    except Exception as e:
        logger.error(f"[HANDLER] Error in Shengxiao handler: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(500, "Error checking compatibility", "CalculationError", str(e))


def handle_luohou_request(params):
    """
    Handle Luohou calculation request

    Args:
        params: Request parameters

    Returns:
        dict: API response
    """
    logger.info("[HANDLER] Processing Luohou request")

    try:
        # Get date parameters with defaults
        from datetime import timedelta

        start_date = params.get('startDate', params.get('start'))
        end_date = params.get('endDate', params.get('end'))

        # Default to next 30 days if not provided
        if not start_date:
            start_date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"[HANDLER] Using default start date: {start_date}")

        if not end_date:
            end_dt = datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=30)
            end_date = end_dt.strftime('%Y-%m-%d')
            logger.info(f"[HANDLER] Using default end date: {end_date}")

        # Validate date format
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError as e:
            logger.warning(f"[HANDLER] Invalid date format: {str(e)}")
            return create_error_response(400, "Date format must be YYYY-MM-DD", "ValidationError", str(e))

        logger.info(f"[HANDLER] Date range: {start_date} to {end_date}")

        # Calculate Luohou dates
        result = LuohouService.calculate_luohou_dates(start_date, end_date)

        response_body = {
            'success': True,
            'data': {
                'startDate': start_date,
                'endDate': end_date,
                'totalDays': len(result),
                'dates': result
            },
            'timestamp': datetime.now(UTC).isoformat()
        }

        return create_response(200, response_body)

    except Exception as e:
        logger.error(f"[HANDLER] Error in Luohou handler: {str(e)}")
        logger.error(traceback.format_exc())
        return create_error_response(500, "Error calculating Luohou dates", "CalculationError", str(e))


# For local testing
if __name__ == "__main__":
    print("="*80)
    print("Testing Lambda Handler Locally")
    print("="*80)

    # Test 1: Health check
    print("\n[TEST 1] Health Check")
    event = {
        'httpMethod': 'GET',
        'path': '/health',
        'queryStringParameters': None,
        'body': None
    }
    response = lambda_handler(event, None)
    print(f"Status: {response['statusCode']}")
    print(f"Body: {response['body'][:200]}...")

    # Test 2: Bazi calculation
    print("\n[TEST 2] Bazi Calculation")
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
    print(f"Status: {response['statusCode']}")
    print(f"Body preview: {response['body'][:500]}...")

    # Test 3: Shengxiao compatibility
    print("\n[TEST 3] Shengxiao Compatibility")
    event = {
        'httpMethod': 'GET',
        'path': '/shengxiao',
        'queryStringParameters': {'zodiac': '虎'},
        'body': None
    }
    response = lambda_handler(event, None)
    print(f"Status: {response['statusCode']}")
    print(f"Body: {response['body'][:300]}...")

    # Test 4: Error handling
    print("\n[TEST 4] Error Handling - Missing Parameters")
    event = {
        'httpMethod': 'POST',
        'path': '/bazi',
        'queryStringParameters': None,
        'body': json.dumps({'year': 1990})
    }
    response = lambda_handler(event, None)
    print(f"Status: {response['statusCode']}")
    print(f"Body: {response['body']}")

    print("\n" + "="*80)
    print("Local testing completed!")
    print("="*80)



