import json
import logging
from typing import Optional, Dict
import aiohttp
import asyncio
from bot.clients.redis_client import RedisClient
from bot.config import settings

# Предполагается, что RedisClient — асинхронный клиент с методами get/set/delete
# settings — объект с LOGIN, SECURITY_KEY, PERSON_ID
# logger — объект для логов

TOKEN_REDIS_KEY = "pyrus:access_token"

logger = logging.getLogger(__name__)

async def fetch_new_token() -> Optional[Dict]:
    """Запрашивает новый токен у Pyrus API"""
    payload = {
        "login": settings.LOGIN,
        "security_key": settings.SECURITY_KEY,
        "person_id": settings.PERSON_ID
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    "https://accounts.pyrus.com/api/v4/auth",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                token_data = await response.json()
                # Не добавляем expires_at
                return token_data
    except Exception as e:
        logger.error(f"Failed to fetch new token: {str(e)}")
        return None


async def get_token_from_cache() -> Optional[Dict]:
    """Получаем токен из Redis"""
    try:
        redis_client = await RedisClient.get_instance()
        token_json = await redis_client.get(TOKEN_REDIS_KEY)
        if token_json is None:
            return None
        return json.loads(token_json)
    except Exception as e:
        logger.error(f"Error reading token from cache: {str(e)}")
        return None


async def save_token_to_cache(token_data: Dict) -> None:
    """Сохраняем токен в Redis без TTL"""
    try:
        redis_client = await RedisClient.get_instance()
        await redis_client.set(TOKEN_REDIS_KEY, json.dumps(token_data))
    except Exception as e:
        logger.error(f"Error saving token to cache: {str(e)}")


async def delete_token_from_cache() -> None:
    """Удаляем токен из Redis"""
    try:
        redis_client = await RedisClient.get_instance()
        await redis_client.delete(TOKEN_REDIS_KEY)
    except Exception as e:
        logger.error(f"Error deleting token from cache: {str(e)}")


async def get_valid_token() -> Optional[str]:
    """
    Получить валидный токен.
    Если в кеше нет токена — получить новый и сохранить.
    """
    token_data = await get_token_from_cache()
    if token_data is None:
        token_data = await fetch_new_token()
        if token_data:
            await save_token_to_cache(token_data)
        else:
            return None
    return token_data.get("access_token")


async def call_pyrus_api(endpoint: str, method="GET", **kwargs):
    """
    Пример вызова Pyrus API с автоматическим обновлением токена при 401.
    """
    token = await get_valid_token()
    if not token:
        logger.error("No valid Pyrus token available")
        return None

    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.pyrus.com/{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, **kwargs) as response:
                if response.status == 401:
                    # Токен просрочен или недействителен — обновляем
                    logger.info("Token expired, fetching new one...")
                    await delete_token_from_cache()
                    new_token_data = await fetch_new_token()
                    if new_token_data:
                        await save_token_to_cache(new_token_data)
                        # Повторяем запрос с новым токеном
                        headers["Authorization"] = f"Bearer {new_token_data['access_token']}"
                        async with session.request(method, url, headers=headers, **kwargs) as retry_response:
                            retry_response.raise_for_status()
                            return await retry_response.json()
                    else:
                        logger.error("Failed to refresh token after 401")
                        return None
                else:
                    response.raise_for_status()
                    return await response.json()

    except Exception as e:
        logger.error(f"Pyrus API call failed: {str(e)}")
        return None


async def periodic_token_refresh(interval_minutes=30):
    """
    Фоновая задача для обновления токена раз в interval_minutes.
    Можно запускать на старте приложения.
    """
    while True:
        try:
            new_token_data = await fetch_new_token()
            if new_token_data:
                await save_token_to_cache(new_token_data)
                logger.info("Pyrus token refreshed successfully")
            else:
                logger.warning("Failed to refresh Pyrus token in periodic task")
        except Exception as e:
            logger.error(f"Error in periodic token refresh: {str(e)}")

        await asyncio.sleep(interval_minutes * 60)
