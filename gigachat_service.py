import os
import json
import re
from typing import Dict, Any
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

SYSTEM_PROMPT = """Ты — интеллектуальный ассистент компании по продаже офисной мебели и услуг (столы, кресла, шкафы, доставка, сборка).
Твоя задача — выполнить строгую первичную обработку входящего обращения клиента.

ПРАВИЛА И КРИТЕРИИ КВАЛИФИКАЦИИ:
1. Квалификация лида (lead_type):
   - "целевой": запрос относится к продуктам компании (офисные столы, кресла, шкафы) или услугам (доставка, сборка мебели) И есть понятное намерение обсудить покупку / заказ.
   - "нецелевой": запрос не относится к товарам и услугам компании (другие товары, сторонний спам и т.п.).
   - "неясно": информации в обращении недостаточно, чтобы уверенно понять суть или намерение.

2. Честность и точность данных:
   - КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать данные, которых нет в тексте.
   - Если параметр (компания, имя, телефон, сроки, бюджет, количество) отсутствует в тексте заявки — укажи строго значение "не указано".
   - Все важные параметры, которых не хватает для оформления заказа (например, объем партии, адрес, реквизиты, спецификация моделей), обязательно перечисли в списке missing_data.

3. Передача человеку (needs_human и human_reason):
   - Установи needs_human: true в случаях:
     * жалобы, претензии, конфликты, срывы сроков (например: заказ задержали, менеджер не отвечает);
     * угрозы отказа от услуг, требования возврата предоплаты или компенсаций;
     * нестандартные или спорные запросы.
   - В поле human_reason обязательно укажи четкую причину передачи человеку.
   - Если повода для срочной передачи нет, установи needs_human: false и human_reason: "Не требуется".

4. Черновик ответа (reply_draft):
   - Вежливый, деловой стиль на русском языке.
   - Никаких выдуманных цен, сроков, скидок и обещаний, которых нет во входных данных!
   - Если информации недостаточно для расчета — задай 1–2 ключевых уточняющих вопроса клиенту.
   - Если это конфликт или жалоба — сформируй нейтральный ответ с подтверждением получения обращения и сообщением, что старший специалист уже разбирается в ситуации (без признания вины и без несогласованных компенсаций).

ФОРМАТ ОТВЕТА:
Верни ответ ИСКЛЮЧИТЕЛЬНО в виде корректного JSON-объекта (без лишнего текста перед и после) со следующей структурой:
{
  "company": "Название компании или 'не указано'",
  "summary": "Краткая суть запроса в 1-2 предложениях",
  "lead_type": "целевой" / "нецелевой" / "неясно",
  "key_data": {
    "продукт": "...",
    "количество": "...",
    "бюджет": "...",
    "сроки": "...",
    "контакты": "..."
  },
  "missing_data": ["параметр 1", "параметр 2"],
  "next_step": "Рекомендуемое действие для менеджера",
  "reply_draft": "Готовый проект сообщения клиенту",
  "needs_human": true / false,
  "human_reason": "Причина передачи человеку или 'Не требуется'"
}
"""


def _clean_json_text(raw_text: str) -> str:
    """Очищает ответ нейросети от markdown-обёрток ```json ... ```"""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def analyze_inquiry(inquiry_text: str) -> Dict[str, Any]:
    """
    Отправляет входящую заявку в GigaChat API и возвращает структурированный словарь.
    """
    # Обновляем переменные из .env при каждом запросе
    load_dotenv(override=True)

    credentials = os.getenv("GIGACHAT_CREDENTIALS", "").strip()
    scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS").strip()
    model = os.getenv("GIGACHAT_MODEL", "GigaChat-2").strip()
    verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").strip().lower() in ("true", "1", "yes")

    if not credentials:
        raise ValueError(
            "Не настроен ключ доступа к GigaChat API! Пожалуйста, скопируйте файл .env.example в .env "
            "и укажите ваш ключ в переменной GIGACHAT_CREDENTIALS."
        )

    # Импортируем официальную библиотеку GigaChat
    try:
        from gigachat import GigaChat
    except ImportError:
        raise RuntimeError("Библиотека 'gigachat' не установлена. Запустите: pip install -r requirements.txt")

    user_message = f"Текст входящей заявки клиента:\n«««\n{inquiry_text}\n»»»\n\nПроанализируй заявку строго по регламенту и верни JSON."

    try:
        with GigaChat(
            credentials=credentials,
            scope=scope,
            model=model,
            verify_ssl_certs=verify_ssl
        ) as giga:
            # Отправляем системный промпт и пользовательскую заявку
            response = giga.chat({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ]
            })

            # Извлекаем текст ответа
            content = ""
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
            elif hasattr(response, "messages") and response.messages:
                content = response.messages[0].content

            if not content:
                raise ValueError("GigaChat вернул пустой ответ.")

            # Очищаем и парсим JSON
            cleaned_json_str = _clean_json_text(content)
            result = json.loads(cleaned_json_str)

            # Гарантируем наличие всех обязательных полей
            required_keys = [
                "company", "summary", "lead_type", "key_data",
                "missing_data", "next_step", "reply_draft",
                "needs_human", "human_reason"
            ]
            for key in required_keys:
                if key not in result:
                    result[key] = "не указано"

            return result

    except json.JSONDecodeError as jde:
        raise ValueError(f"Ошибка разбора ответа модели. Модель вернула текст вместо JSON:\n{content}") from jde
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg or "Invalid client" in error_msg:
            raise PermissionError(
                "Ошибка авторизации GigaChat (401). Проверьте правильность ключа GIGACHAT_CREDENTIALS и параметра GIGACHAT_SCOPE в файле .env."
            ) from e
        if "certificate" in error_msg.lower() or "ssl" in error_msg.lower():
            raise ConnectionError(
                "Ошибка проверки SSL-сертификата. Убедитесь, что в файле .env параметр GIGACHAT_VERIFY_SSL_CERTS установлен в false."
            ) from e
        raise e
