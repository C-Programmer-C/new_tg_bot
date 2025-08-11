def get_value_by_item_id(item_id, data):
    for item in data:
        if item['item_id'] == item_id:
            return item['values'][0]  # Возвращаем первое значение из массива values
    return None