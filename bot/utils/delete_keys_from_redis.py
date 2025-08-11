from typing import Any
from redis.asyncio import Redis


async def delete_keys_by_pattern_async(
        redis_client: Redis,
        pattern: str,
        scan_batch: int = 1000,
        delete_batch: int = 500,
) -> bool:
    """
    Удаляет все ключи, соответствующие шаблону pattern, пакетами.

    - scan_batch: сколько ключей Redis будет возвращать за один SCAN.
    - delete_batch: максимальное число ключей в одном DELETE/UNLINK.

    Возвращает True, если были удалены ключи, иначе False.
    """
    cursor = 0
    buffer: list[Any] = []
    keys_found = False

    # Проверяем наличие ключей перед началом удаления
    while True:
        cursor, keys = await redis_client.scan(
            cursor=cursor,
            match=pattern,
            count=scan_batch,
        )
        if keys:
            keys_found = True  # Ключи найдены
            buffer.extend(keys)

        if cursor == 0:
            break

    if not keys_found:
        return False  # Если не найдено ни одного ключа, возвращаем False

    # Удаляем ключи, если они были найдены
    while len(buffer) >= delete_batch:
        chunk = buffer[:delete_batch]
        buffer = buffer[delete_batch:]
        await redis_client.unlink(*chunk)

    # Удаляем остаток, если он есть
    if buffer:
        await redis_client.unlink(*buffer)

    return True  # Возвращаем True, если были удалены ключи
