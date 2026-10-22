import os
import re
import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def _extract_numeric_budget(budget_str: str) -> Optional[float]:
    """Извлекает числовое значение бюджета (например, '1,5 млн рублей' -> 1500000)"""
    if not budget_str or "не указан" in budget_str.lower():
        return None

    clean = budget_str.lower().replace(" ", "").replace(",", ".")
    match = re.search(r'(\d+(?:\.\d+)?)', clean)
    if not match:
        return None

    num = float(match.group(1))
    if "млн" in clean:
        return num * 1_000_000
    elif "тыс" in clean or "к" in clean:
        return num * 1_000
    elif num > 0:
        return num
    return None


def _get_b24_base_domain(b24_url: str) -> str:
    """Извлекает базовый домен портала из URL вебхука"""
    parsed = urllib.parse.urlparse(b24_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _post_b24(url: str, payload: Dict[str, Any], timeout: int = 25) -> Dict[str, Any]:
    """Отправляет POST-запрос к API Битрикс24 через встроенную библиотеку urllib"""
    body_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body_bytes,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    last_err = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                resp_text = response.read().decode("utf-8")
                return json.loads(resp_text)
        except Exception as err:
            last_err = err
    raise last_err or RuntimeError("Не удалось выполнить запрос к Битрикс24")


def send_lead_to_bitrix24(result_data: Dict[str, Any], client_inputs: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Создает лид в CRM Битрикс24, при необходимости ставит задачу и отправляет уведомление.
    """
    load_dotenv(override=True)
    b24_url = os.getenv("B24_URL", "").strip()

    if not b24_url:
        return {
            "success": False,
            "skipped": True,
            "message": "Переменная B24_URL не заполнена в .env. Синхронизация с CRM пропущена."
        }

    # Нормализуем URL вебхука со слэшем на конце
    if not b24_url.endswith("/"):
        b24_url += "/"

    base_domain = _get_b24_base_domain(b24_url)
    client_inputs = client_inputs or {}

    # Получаем восстановленные данные
    company = result_data.get("company", "").strip()
    if company.lower() in ("не указано", "не указана"):
        company = client_inputs.get("company", "").strip()

    name = client_inputs.get("name", "").strip()
    phone = client_inputs.get("phone", "").strip()
    summary = result_data.get("summary", "Заявка с сайта").strip()
    lead_type = result_data.get("lead_type", "неясно").strip()
    needs_human = result_data.get("needs_human", False)
    human_reason = result_data.get("human_reason", "").strip()
    next_step = result_data.get("next_step", "").strip()
    reply_draft = result_data.get("reply_draft", "").strip()
    key_data = result_data.get("key_data") or {}
    missing_data = result_data.get("missing_data") or []

    # Определяем заголовок лида
    identifier = company if (company and company.lower() not in ("не указано", "не указана")) else (name or "Клиент")
    lead_title = f"[{lead_type.capitalize()}] {identifier}: {summary[:80]}"

    # Формируем красивое HTML-описание для карточки CRM
    comments_parts = [
        f"<h3>🤖 AI-Анализ входящей заявки (GigaChat)</h3>",
        f"<p><b>Квалификация лида:</b> {lead_type.capitalize()}</p>",
        f"<p><b>Краткая суть:</b> {summary}</p>",
        f"<p><b>Рекомендуемый следующий шаг:</b> {next_step}</p>",
        "<hr>"
    ]

    # Известные параметры
    if isinstance(key_data, dict) and key_data:
        comments_parts.append("<p><b>Известные параметры заказа:</b></p><ul>")
        for k, v in key_data.items():
            comments_parts.append(f"<li><b>{k}:</b> {v}</li>")
        comments_parts.append("</ul>")

    # Недостающие данные
    if missing_data and isinstance(missing_data, list):
        comments_parts.append("<p><b>Чего не хватает для расчета:</b></p><ul>")
        for m in missing_data:
            comments_parts.append(f"<li>{m}</li>")
        comments_parts.append("</ul>")

    # Черновик ответа
    if reply_draft:
        comments_parts.append(f"<hr><p><b>💬 Подготовленный черновик ответа клиенту:</b></p><blockquote>{reply_draft}</blockquote>")

    # Предупреждение о передаче человеку
    if needs_human:
        comments_parts.append(f"<hr><p style='color:red;'><b>🚨 ВНИМАНИЕ: Требуется вмешательство человека!</b><br>Причина: {human_reason}</p>")

    # Исходное обращение
    raw_text = client_inputs.get("raw_text", "").strip()
    if raw_text:
        comments_parts.append(f"<hr><p><b>📄 Исходный текст обращения:</b><br>{raw_text}</p>")

    comments_html = "".join(comments_parts)

    # Собираем поля для crm.lead.add
    lead_fields: Dict[str, Any] = {
        "TITLE": lead_title,
        "COMMENTS": comments_html,
        "STATUS_ID": "NEW",
        "SOURCE_ID": "WEB",
        "CURRENCY_ID": "RUB"
    }

    if name and name.lower() not in ("не указано", "не указан"):
        lead_fields["NAME"] = name

    if company and company.lower() not in ("не указано", "не указана"):
        lead_fields["COMPANY_TITLE"] = company

    if phone and phone.lower() not in ("не указано", "не указан"):
        lead_fields["PHONE"] = [{"VALUE": phone, "VALUE_TYPE": "WORK"}]

    # Попытка извлечь бюджет
    budget_candidate = key_data.get("бюджет", "") if isinstance(key_data, dict) else ""
    numeric_budget = _extract_numeric_budget(str(budget_candidate))
    if numeric_budget:
        lead_fields["OPPORTUNITY"] = numeric_budget

    output_info: Dict[str, Any] = {
        "success": False,
        "lead_id": None,
        "lead_url": None,
        "task_id": None,
        "task_url": None,
        "notification_sent": False
    }

    try:
        # 1. Создаем Лид в CRM (crm.lead.add)
        lead_data = _post_b24(f"{b24_url}crm.lead.add.json", {"fields": lead_fields}, timeout=25)

        if "result" not in lead_data:
            raise RuntimeError(f"Ошибка создания лида в Битрикс24: {lead_data.get('error_description', lead_data)}")

        lead_id = lead_data["result"]
        lead_url = f"{base_domain}/crm/lead/details/{lead_id}/"

        output_info["success"] = True
        output_info["lead_id"] = lead_id
        output_info["lead_url"] = lead_url

        # 2. Если требуется участие человека (needs_human), ставим срочную задачу (tasks.task.add)
        task_id = None
        if needs_human:
            task_title = f"🚨 СРОЧНО: {human_reason} (Лид #{lead_id})"
            task_desc = (
                f"Поступило обращение клиента, требующее оперативного вмешательства!\n\n"
                f"Клиент / Компания: {identifier}\n"
                f"Причина: {human_reason}\n"
                f"Суть обращения: {summary}\n\n"
                f"Черновик ответа:\n{reply_draft}\n\n"
                f"Ссылка на лид в CRM: {lead_url}"
            )

            task_payload = {
                "fields": {
                    "TITLE": task_title,
                    "DESCRIPTION": task_desc,
                    "PRIORITY": "2",  # Высокий приоритет
                    "UF_CRM_TASK": [f"L_{lead_id}"],  # Привязка к созданному лиду
                    "RESPONSIBLE_ID": 1,
                    "DEADLINE": ""
                }
            }
            try:
                task_json = _post_b24(f"{b24_url}tasks.task.add.json", task_payload, timeout=20)
                if "result" in task_json and "task" in task_json["result"]:
                    task_id = task_json["result"]["task"]["id"]
                    output_info["task_id"] = task_id
                    output_info["task_url"] = f"{base_domain}/company/personal/user/1/tasks/task/view/{task_id}/"
            except Exception as task_err:
                print(f"[Warning] Не удалось создать задачу в Битрикс24: {task_err}")

        # 3. Отправляем системное уведомление в колокольчик (im.notify.personal.add)
        try:
            if needs_human:
                notify_msg = (
                    f"🚨 [B]ВНИМАНИЕ![/B] Поступило срочное обращение клиента: [URL={lead_url}]Лид #{lead_id}[/URL].\n"
                    f"Причина: {human_reason}."
                )
                if task_id:
                    notify_msg += f"\nПоставлена срочная [URL={output_info['task_url']}]Задача #{task_id}[/URL]."
            else:
                notify_msg = (
                    f"📥 [B]Новый лид в CRM:[/B] [URL={lead_url}]#{lead_id} {lead_title}[/URL]\n"
                    f"Квалификация: {lead_type.capitalize()}."
                )

            notify_payload = {
                "USER_ID": 1,
                "MESSAGE": notify_msg
            }
            notify_json = _post_b24(f"{b24_url}im.notify.personal.add.json", notify_payload, timeout=15)
            if notify_json.get("result"):
                output_info["notification_sent"] = True
        except Exception as notify_err:
            print(f"[Warning] Не удалось отправить уведомление в Битрикс24: {notify_err}")

        return output_info

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "lead_id": None
        }
