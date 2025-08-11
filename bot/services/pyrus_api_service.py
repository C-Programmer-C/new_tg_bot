import asyncio
import json
import logging
import aiohttp
from typing import List, Dict, Optional, Any
from bot.config import settings
from bot.utils.build_payload import build_payload
from bot.services.pyrus_auth_service import get_valid_token, delete_token_from_cache, \
    save_token_to_cache, fetch_new_token
from aiohttp import FormData

logger = logging.getLogger(__name__)


class PyrusService:
    # Конфигурация API endpoints
    _API_BASE = "https://api.pyrus.com/v4"
    _ENDPOINTS = {
        'items': "/catalogs/267947",
        'contractors': "/forms/2306222/register",
        'users': "/forms/2304966/register",
        'tasks': "/forms/2303165/register"
    }

    _REQUEST_TIMEOUT = 5.0

    @classmethod
    async def _make_request(
            cls,
            endpoint: str,
            method: str = "GET",
            json_data: Optional[Dict] = None,
            timeout: Optional[int] = None,
            data: Optional[FormData] = None
    ) -> Any:
        token = await get_valid_token()
        if not token:
            return None

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        url = f"{cls._API_BASE}{endpoint}"

        try:
            async with aiohttp.ClientSession() as session:
                # Выполняем первоначальный запрос
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, timeout=timeout) as response:
                        return await cls._handle_request_with_token_refresh(
                            session, response, endpoint, method, json_data, timeout, data
                        )

                elif method.upper() == "POST":
                    if data:
                        async with session.post(url, data=data, headers=headers, timeout=timeout) as response:
                            return await cls._handle_request_with_token_refresh(
                                session, response, endpoint, method, json_data, timeout, data
                            )
                    else:
                        async with session.post(url, json=json_data, headers=headers, timeout=timeout) as response:
                            return await cls._handle_request_with_token_refresh(
                                session, response, endpoint, method, json_data, timeout, data
                            )

                logger.error(f"Unsupported HTTP method: {method}")
                return None

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Network error: {type(e).name} - {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error: {str(e)}")
        return None

    @classmethod
    async def _handle_request_with_token_refresh(
            cls,
            session: aiohttp.ClientSession,
            response: aiohttp.ClientResponse,
            endpoint: str,
            method: str,
            json_data: Optional[Dict] = None,
            timeout: Optional[int] = None,
            data: Optional[FormData] = None
    ) -> Any:
        """Обрабатывает ответ, обновляя токен при необходимости"""
        # Если ответ не 401, просто обрабатываем его
        if response.status != 401:
            return await cls._handle_response(
                response,
                f"{cls._API_BASE}{endpoint}",
                request_data=json_data
            )

        logger.info("Token expired, fetching new one...")
        await delete_token_from_cache()

        # Получаем новый токен
        if not (new_token_data := await fetch_new_token()):
            logger.error("Failed to refresh token after 401")
            return None

        await save_token_to_cache(new_token_data)
        new_token = new_token_data["access_token"]

        # Формируем новые заголовки
        headers = {
            "Authorization": f"Bearer {new_token}",
            "Accept": "application/json"
        }

        # Подготавливаем параметры для повторного запроса
        request_params = {
            "url": f"{cls._API_BASE}{endpoint}",
            "headers": headers,
            "timeout": timeout or cls._REQUEST_TIMEOUT
        }

        # Добавляем данные в зависимости от типа запроса
        if data:
            request_params["data"] = data
        elif json_data:
            request_params["json"] = json_data

        logger.debug(f"Retrying request with new token: {method} {request_params['url']}")

        # Выполняем повторный запрос
        try:
            if method.upper() == "GET":
                async with session.get(**request_params) as retry_response:
                    return await cls._handle_response(retry_response, request_params['url'])

            elif method.upper() == "POST":
                async with session.post(**request_params) as retry_response:
                    return await cls._handle_response(
                        retry_response,
                        request_params['url'],
                        request_data=json_data
                    )

            logger.error(f"Unsupported HTTP method for retry: {method}")
            return None

        except Exception as e:
            logger.error(f"Error during retry request: {str(e)}")
            return None

    @staticmethod
    async def _handle_response(response: aiohttp.ClientResponse, url: str, request_data: Optional[Dict] = None) -> Any:
        """Обрабатывает ответ от API"""
        try:
            # Успешные ответы (2xx)
            if 200 <= response.status < 300:
                content_type = response.headers.get('Content-Type', '')
                if 'application/json' in content_type:
                    try:
                        return await response.json()
                    except Exception as e:
                        logger.warning(f"JSON parse warning: {str(e)}")
                        return await response.text()
                return await response.text()

            # Обработка ошибок
            error_text = await response.text()
            logger.error(f"Request failed: {response.status} {url}")
            if request_data:
                logger.error(f"Request payload: {json.dumps(request_data, indent=2)}")
            logger.error(f"Response: {error_text[:500]}")
            return None

        except Exception as e:
            logger.exception(f"Response handling error: {str(e)}")
            return None

    @staticmethod
    async def _get_error_body(response: aiohttp.ClientResponse) -> str:
        """Получение тела ошибки безопасным способом"""
        try:
            return await response.text()
        except Exception:
            return "<unable to retrieve error body>"

    @classmethod
    async def get_items(cls) -> List[Dict]:
        """Получение элементов каталога"""
        data = await cls._make_request(cls._ENDPOINTS['items'])
        return data.get('items', []) if data else []

    @classmethod
    async def get_contractors(cls) -> List[Dict]:
        """Получение списка подрядчиков"""
        data = await cls._make_request(cls._ENDPOINTS['contractors'])
        return data.get('tasks', []) if data else []

    @classmethod
    async def get_users(cls) -> List[Dict]:
        """Получение списка пользователей"""
        data = await cls._make_request(cls._ENDPOINTS['users'])
        return data.get('tasks', []) if data else []

    @classmethod
    async def get_tasks(cls) -> List[Dict]:
        """Получение списка задач"""
        data = await cls._make_request(cls._ENDPOINTS['tasks'])
        return data.get('tasks', []) if data else []

    @classmethod
    async def create_task(cls, json_data) -> List[Dict]:
        """Создание задачи в Pyrus по API"""
        return await cls._make_request(endpoint="/tasks", method="POST", json_data=json_data)

    @classmethod
    async def get_task_by_id(cls, task_id: int):
        """Поиск задачи в Pyrus по известной id задачи с помощью API"""
        return await cls._make_request(endpoint=f"/tasks/{task_id}", method="GET")

    @classmethod
    async def get_unique_file_id(cls, file_bytes, filename):
        """Получение id файла при его загрузке по API в Pyrus"""
        form = FormData(quote_fields=False)
        form.add_field(
            name='file',
            value=file_bytes,
            filename=filename,
            content_type='application/octet-stream'
        )

        result = await cls._make_request(
            endpoint="/files/upload",
            method="POST",
            data=form
        )
        return result.get("guid")

    @classmethod
    async def post_comment_files(cls, task_id: int, text: Optional[str], files: Optional[List[str]]):
        json_data = build_payload(text, files)
        return await cls._make_request(endpoint=f"/tasks/{task_id}/comments", method="POST", json_data=json_data)

    @classmethod
    async def post_comment_value_fields(cls, task_id: int, json_data: Dict):
        return await cls._make_request(endpoint=f"/tasks/{task_id}/comments", method="POST", json_data=json_data)


    @classmethod
    async def get_closed_tasks(cls, closed_after: str):
        json_data = {"closed_after": closed_after}
        form_id = settings.FORM_TASKS_ID
        result = await cls._make_request(endpoint=f"/forms/{form_id}/register", method="POST", json_data=json_data)
        return result.get("tasks", [])

    @classmethod
    async def close_task(cls, task_id: int, text: str = None):
        json_data = {"text": text, "action": "finished"}
        result = await cls._make_request(endpoint=f"/tasks/{task_id}/comments", method="POST", json_data=json_data)
        return result.get("task", []).get("id")

    @classmethod
    async def open_task(cls, task_id: int, text: str = None):
        json_data = {"text": text, "action": "reopened"}
        result = await cls._make_request(endpoint=f"/tasks/{task_id}/comments", method="POST", json_data=json_data)
        return result.get("task", []).get("id")



