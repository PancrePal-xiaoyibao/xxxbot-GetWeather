import sys
import subprocess
import importlib.util
import asyncio
import logging
import time
import os

# 检查并安装必要的依赖
def check_and_install_dependencies():
    """检查并安装必要的依赖"""
    required_packages = {
        'aiohttp': 'aiohttp',
        'PyJWT': 'jwt',
        'cryptography': 'cryptography'
    }

    for package, import_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            print(f"正在安装依赖: {package}")
            try:
                # 使用清华源安装
                subprocess.check_call([
                    sys.executable, 
                    "-m", 
                    "pip", 
                    "install", 
                    package,
                    "-i", 
                    "https://pypi.tuna.tsinghua.edu.cn/simple",
                    "--trusted-host", 
                    "pypi.tuna.tsinghua.edu.cn"
                ])
                print(f"成功安装 {package}")
            except subprocess.CalledProcessError as e:
                print(f"安装 {package} 失败: {str(e)}")
                raise RuntimeError(f"无法安装必要的依赖: {package}")

# 安装依赖
check_and_install_dependencies()

# 现在导入其他模块
import aiohttp
import jwt
import tomllib

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置信息 - 更新为新的参数
API_HOST = "https://ky5n8ka83w.re.qweatherapi.com"
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIHH0kbBmRxpBLwKQwVZIszIbEBuvGdQHXxuT+0jViEwk
-----END PRIVATE KEY-----"""
JWT_KID = "KBB6BKVM5T"
JWT_SUB = "2NTGFT493T"

def generate_jwt_token():
    """生成JWT token"""
    try:
        # 构建payload
        payload = {
            'iat': int(time.time()) - 30,  # 当前时间前30秒
            'exp': int(time.time()) + 900,  # 15分钟后过期
            'sub': JWT_SUB
        }
        
        # 构建headers
        headers = {
            'kid': JWT_KID
        }
        
        # 记录详细信息
        logger.info("JWT生成信息:")
        logger.info(f"当前时间戳: {int(time.time())}")
        logger.info(f"iat时间戳: {payload['iat']}")
        logger.info(f"exp时间戳: {payload['exp']}")
        logger.info(f"JWT Headers: {headers}")
        logger.info(f"JWT Payload: {payload}")
        
        # 生成token
        token = jwt.encode(payload, PRIVATE_KEY, algorithm='EdDSA', headers=headers)
        logger.info(f"生成的Token: {token}")
        return token
        
    except Exception as e:
        logger.error(f"生成JWT token失败: {str(e)}")
        raise

async def test_weather_api():
    """测试天气API"""
    try:
        # 生成JWT token
        token = generate_jwt_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        # 1. 查询城市信息
        city = "beijing"
        geo_url = f"{API_HOST}/geo/v2/city/lookup?location={city}"
        logger.info(f"\n请求城市查询API:")
        logger.info(f"URL: {geo_url}")
        logger.info(f"Headers: {headers}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                geo_url, 
                headers=headers,
                compress=True
            ) as response:
                response_text = await response.text()
                logger.info(f"响应状态码: {response.status}")
                logger.info(f"响应头: {dict(response.headers)}")
                logger.info(f"响应内容: {response_text}")
                
                if response.status != 200:
                    logger.error(f"城市查询API请求失败: {response.status}")
                    return
                
                geo_data = await response.json()
                if geo_data['code'] != '200':
                    logger.error(f"城市查询失败: {geo_data}")
                    return
                
                city_id = geo_data["location"][0]["id"]
                logger.info(f"获取到城市ID: {city_id}")
                
            # 2. 查询实时天气
            now_url = f"{API_HOST}/v7/weather/now?location={city_id}"
            logger.info(f"请求实时天气API: {now_url}")
            
            async with session.get(
                now_url, 
                headers=headers,
                compress=True
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"实时天气API请求失败: {response.status}")
                    logger.error(f"错误响应: {error_text}")
                    return
                
                now_data = await response.json()
                logger.info(f"实时天气API响应: {now_data}")
                
                if now_data['code'] != '200':
                    logger.error(f"获取实时天气失败: {now_data}")
                    return
                
                # 打印实时天气信息
                now = now_data['now']
                logger.info(f"\n实时天气信息:")
                logger.info(f"温度: {now['temp']}℃")
                logger.info(f"体感温度: {now['feelsLike']}℃")
                logger.info(f"天气: {now['text']}")
                logger.info(f"风向: {now['windDir']}")
                logger.info(f"风力等级: {now['windScale']}级")
                logger.info(f"相对湿度: {now['humidity']}%")
                logger.info(f"降水量: {now['precip']}mm")
                logger.info(f"能见度: {now['vis']}km")
            
            # 3. 查询7天预报
            forecast_url = f"{API_HOST}/v7/weather/7d?location={city_id}"
            logger.info(f"请求7天预报API: {forecast_url}")
            
            async with session.get(
                forecast_url, 
                headers=headers,
                compress=True
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"7天预报API请求失败: {response.status}")
                    logger.error(f"错误响应: {error_text}")
                    return
                
                forecast_data = await response.json()
                logger.info(f"7天预报API响应: {forecast_data}")
                
                if forecast_data['code'] != '200':
                    logger.error(f"获取7天预报失败: {forecast_data}")
                    return
                
                # 打印7天预报信息
                logger.info(f"\n7天天气预报:")
                for day in forecast_data['daily']:
                    logger.info(f"\n日期: {day['fxDate']}")
                    logger.info(f"白天天气: {day['textDay']}")
                    logger.info(f"夜间天气: {day['textNight']}")
                    logger.info(f"最高温度: {day['tempMax']}℃")
                    logger.info(f"最低温度: {day['tempMin']}℃")
                    logger.info(f"风向: {day['windDirDay']}")
                    logger.info(f"风力等级: {day['windScaleDay']}级")
                    logger.info(f"相对湿度: {day['humidity']}%")
                    logger.info(f"紫外线指数: {day['uvIndex']}")
                    logger.info(f"能见度: {day['vis']}km")
                    logger.info(f"日出时间: {day['sunrise']}")
                    logger.info(f"日落时间: {day['sunset']}")
                    logger.info(f"月升时间: {day['moonrise']}")
                    logger.info(f"月落时间: {day['moonset']}")
                    logger.info(f"月相: {day['moonPhase']}")
                    logger.info(f"降水概率: {day['precip']}%")
                    
    except Exception as e:
        logger.error(f"测试过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_weather_api()) 