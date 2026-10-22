import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from gigachat_service import analyze_inquiry
from anonymizer import Anonymizer
from bitrix24_service import send_lead_to_bitrix24

# Загружаем настройки окружения
load_dotenv()

app = Flask(__name__)

# Предустановленные тестовые заявки из задания с разбивкой по полям формы
TEST_INQUIRIES = {
    "test1": {
        "company": "Альфа-Логистик",
        "name": "Офис-менеджер",
        "phone": "",
        "text": (
            "Здравствуйте! Мы переезжаем в новый офис на 40 рабочих мест "
            "и хотим заказать поставку и сборку офисной мебели: столы, кресла и шкафы. "
            "Переезд — в начале следующего месяца, бюджет около 1,5 млн рублей. "
            "Пришлите, пожалуйста, коммерческое предложение."
        )
    },
    "test2": {
        "company": "",
        "name": "",
        "phone": "",
        "text": (
            "Добрый день, сколько у вас стоят офисные кресла? "
            "Нужно несколько штук."
        )
    },
    "test3": {
        "company": "",
        "name": "",
        "phone": "",
        "text": (
            "Это уже третье письмо! Заказ должны были привезти в понедельник, "
            "сейчас четверг — ни мебели, ни звонка. Менеджер не берёт трубку. "
            "Если завтра ничего не изменится, будем отказываться и требовать "
            "возврат предоплаты."
        )
    }
}


@app.route("/")
def index():
    """Главная страница приложения"""
    return render_template("index.html", test_inquiries=TEST_INQUIRIES)


@app.route("/api/process", methods=["POST"])
def process_inquiry():
    """Эндпоинт для обработки данных формы через GigaChat API"""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    company = (data.get("company") or "").strip()

    # Собираем данные формы в понятный текстовый запрос для AI
    full_inquiry_parts = []
    if company:
        full_inquiry_parts.append(f"Компания / организация: {company}")
    if name:
        full_inquiry_parts.append(f"Имя клиента / контактное лицо: {name}")
    if phone:
        full_inquiry_parts.append(f"Телефон / способ связи: {phone}")
    if text:
        full_inquiry_parts.append(f"Суть обращения / заявка: {text}")

    full_inquiry = "\n".join(full_inquiry_parts).strip()

    if not full_inquiry:
        return jsonify({
            "success": False,
            "error": "Форма пуста. Пожалуйста, укажите имя, телефон или текст обращения."
        }), 400

    try:
        # 1. Анонимизируем персональные данные перед отправкой в AI
        anonymized_inquiry, pii_mapping, detected_pii = Anonymizer.anonymize(
            full_inquiry,
            explicit_entities={"name": name, "phone": phone}
        )

        # 2. Нейросеть обрабатывает исключительно обезличенный текст
        raw_result = analyze_inquiry(anonymized_inquiry)

        # 3. Восстанавливаем оригинальные данные обратно в результат
        restored_result = Anonymizer.deanonymize(raw_result, pii_mapping)

        # 4. Отправляем заявку в CRM Битрикс24 (если настроен B24_URL)
        b24_info = send_lead_to_bitrix24(
            restored_result,
            client_inputs={
                "name": name,
                "phone": phone,
                "company": company,
                "raw_text": text
            }
        )

        return jsonify({
            "success": True,
            "data": restored_result,
            "anonymized_text": anonymized_inquiry,
            "anonymization_info": {
                "detected_count": len(detected_pii),
                "detected_types": [item["type"] for item in detected_pii]
            },
            "bitrix24": b24_info
        })
    except PermissionError as pe:
        return jsonify({
            "success": False,
            "error": str(pe)
        }), 401
    except ValueError as ve:
        return jsonify({
            "success": False,
            "error": str(ve)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Произошла ошибка при обращении к AI-сервису: {str(e)}"
        }), 500


if __name__ == "__main__":
    # Запуск локального сервера разработки
    print("=" * 60)
    print(" AI-помощник обработки входящих заявок запущен!")
    print(" Откройте в браузере: http://127.0.0.1:5000")
    print(" Для остановки нажмите Ctrl + C")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)
