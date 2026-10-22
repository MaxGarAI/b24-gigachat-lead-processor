import re
from typing import Dict, Tuple, List, Any, Optional


class Anonymizer:
    """
    Слой защиты и анонимизации персональных данных (PII).
    Обезличивает имена, телефоны, email и адреса перед отправкой в нейросеть,
    хранит соответствия только в оперативной памяти запроса
    и восстанавливает оригинальные данные в полученном ответе.
    """

    # Регулярные выражения для поиска ПДн
    EMAIL_REGEX = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        re.IGNORECASE
    )

    # Телефонные номера (различные форматы РФ и международные)
    PHONE_REGEX = re.compile(
        r'(?:\+?7|8)?[\s\-\(]*\d{3}[\s\-\)]*[\s\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}\b|'
        r'\b\d{3}[\s\-]\d{2}[\s\-]\d{2}\b'
    )

    # Адреса (улицы, города, дома, офисы)
    ADDRESS_REGEX = re.compile(
        r'(?:(?:г\.|город|пос\.|село)\s+[А-ЯЁа-яё\-]+,\s*)?'
        r'(?:ул\.|улица|пр-кт|проспект|наб\.|набережная|пер\.|переулок|ш\.|шоссе|бульвар|б-р)\s+'
        r'[А-ЯЁа-яё0-9\s\-]+?'
        r'(?:,\s*(?:д\.|дом|кв\.|оф\.|офис|стр\.|строение|корп\.|корпус)\s*\d+[А-ЯЁа-яё0-9\/\-]*)?'
        r'(?=[,\.\n;]|$)',
        re.IGNORECASE
    )

    # Имена в тексте (по типовым маркерам)
    NAME_PATTERNS = [
        re.compile(r'(?:меня зовут|я\s*—|я\s*-|мое имя:?|моё имя:?)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)', re.IGNORECASE),
        re.compile(r'(?:обращаться к|контактное лицо:?|менеджер:?)\s+([А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)', re.IGNORECASE),
    ]

    @classmethod
    def anonymize(
        cls,
        text: str,
        explicit_entities: Optional[Dict[str, str]] = None
    ) -> Tuple[str, Dict[str, str], List[Dict[str, str]]]:
        """
        Анонимизирует текст заявки.

        Параметры:
            text: Исходный текст заявки.
            explicit_entities: Явные поля из формы (например, {"name": "...", "phone": "..."}).

        Возвращает:
            anonymized_text: Обезличенный текст с токенами [ИМЯ_1], [ТЕЛЕФОН_1] и т.д.
            token_to_real: Словарь соответствия токен -> реальное значение (хранится только в памяти).
            detected_items: Список обнаруженных сущностей для отображения пользователю.
        """
        token_to_real: Dict[str, str] = {}
        real_to_token: Dict[str, str] = {}
        detected_items: List[Dict[str, str]] = []

        counters = {
            "ИМЯ": 0,
            "ТЕЛЕФОН": 0,
            "EMAIL": 0,
            "АДРЕС": 0
        }

        def get_or_create_token(entity_type: str, original_value: str) -> str:
            clean_val = original_value.strip()
            if not clean_val or len(clean_val) < 2:
                return original_value

            if clean_val in real_to_token:
                return real_to_token[clean_val]

            counters[entity_type] += 1
            token = f"[{entity_type}_{counters[entity_type]}]"
            real_to_token[clean_val] = token
            token_to_real[token] = clean_val
            detected_items.append({
                "type": entity_type,
                "token": token,
                "original": clean_val
            })
            return token

        result_text = text

        # 1. Сначала обрабатываем явные данные из формы (если переданы)
        if explicit_entities:
            # Имя из формы
            explicit_name = (explicit_entities.get("name") or "").strip()
            if explicit_name:
                token = get_or_create_token("ИМЯ", explicit_name)
                # Заменяем вхождение имени с сохранением границ слов
                result_text = re.sub(re.escape(explicit_name), token, result_text, flags=re.IGNORECASE)

            # Телефон из формы
            explicit_phone = (explicit_entities.get("phone") or "").strip()
            if explicit_phone:
                token = get_or_create_token("ТЕЛЕФОН", explicit_phone)
                result_text = re.sub(re.escape(explicit_phone), token, result_text, flags=re.IGNORECASE)

        # 2. Поиск и замена Email-адресов
        for match in list(cls.EMAIL_REGEX.finditer(result_text)):
            email = match.group(0)
            token = get_or_create_token("EMAIL", email)
            result_text = result_text.replace(email, token)

        # 3. Поиск и замена номеров телефонов в свободном тексте
        for match in list(cls.PHONE_REGEX.finditer(result_text)):
            phone = match.group(0).strip()
            # Пропускаем единичные короткие числа (например '40' мест или '1,5' млн)
            digits_count = len(re.findall(r'\d', phone))
            if digits_count >= 7:
                token = get_or_create_token("ТЕЛЕФОН", phone)
                result_text = result_text.replace(phone, token)

        # 4. Поиск и замена адресов доставки / офисов
        for match in list(cls.ADDRESS_REGEX.finditer(result_text)):
            addr = match.group(0).strip()
            if len(addr) > 5:
                token = get_or_create_token("АДРЕС", addr)
                result_text = result_text.replace(addr, token)

        # 5. Поиск имен по фразовым маркерам в тексте
        for pattern in cls.NAME_PATTERNS:
            for match in list(pattern.finditer(result_text)):
                name = match.group(1).strip()
                if len(name) > 2 and not name.startswith("["):
                    token = get_or_create_token("ИМЯ", name)
                    result_text = result_text.replace(name, token)

        return result_text, token_to_real, detected_items

    @classmethod
    def deanonymize(cls, data: Any, token_to_real: Dict[str, str]) -> Any:
        """
        Рекурсивно подставляет настоящие персональные данные вместо временных токенов
        в полученном от нейросети результате.
        """
        if not token_to_real:
            return data

        if isinstance(data, str):
            res = data
            for token, real_val in token_to_real.items():
                # Точная замена токена
                res = res.replace(token, real_val)
                # На случай, если LLM добавила пробелы внутри скобок (например, [ ТЕЛЕФОН_1 ])
                inner = token[1:-1]
                spaced_pattern = re.compile(rf'\[\s*{re.escape(inner)}\s*\]', re.IGNORECASE)
                res = spaced_pattern.sub(real_val, res)
            return res

        elif isinstance(data, dict):
            return {
                cls.deanonymize(k, token_to_real): cls.deanonymize(v, token_to_real)
                for k, v in data.items()
            }

        elif isinstance(data, list):
            return [cls.deanonymize(item, token_to_real) for item in data]

        return data
