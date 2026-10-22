document.addEventListener("DOMContentLoaded", () => {
  // Элементы формы заявки
  const clientName = document.getElementById("clientName");
  const clientPhone = document.getElementById("clientPhone");
  const clientCompany = document.getElementById("clientCompany");
  const inquiryText = document.getElementById("inquiryText");
  const processBtn = document.getElementById("processBtn");
  const clearTextBtn = document.getElementById("clearTextBtn");

  // Кнопки тестовых сценариев
  const preset1Btn = document.getElementById("preset1Btn");
  const preset2Btn = document.getElementById("preset2Btn");
  const preset3Btn = document.getElementById("preset3Btn");

  // Блоки состояний
  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const resultCard = document.getElementById("resultCard");

  // Баннер ошибки
  const errorBanner = document.getElementById("errorBanner");
  const errorTitle = document.getElementById("errorTitle");
  const errorMessage = document.getElementById("errorMessage");
  const closeErrorBtn = document.getElementById("closeErrorBtn");

  // Поля результата
  const leadTypeBadge = document.getElementById("leadTypeBadge");
  const needsHumanBadge = document.getElementById("needsHumanBadge");
  const privacyAlertBox = document.getElementById("privacyAlertBox");
  const privacyAlertText = document.getElementById("privacyAlertText");
  const anonymizedModule = document.getElementById("anonymizedModule");
  const anonymizedTextValue = document.getElementById("anonymizedTextValue");
  const anonymizedContentBox = document.getElementById("anonymizedContentBox");
  const toggleAnonBtn = document.getElementById("toggleAnonBtn");
  const b24AlertBox = document.getElementById("b24AlertBox");
  const b24StatusBadge = document.getElementById("b24StatusBadge");
  const b24Description = document.getElementById("b24Description");
  const b24LeadLink = document.getElementById("b24LeadLink");
  const b24TaskLink = document.getElementById("b24TaskLink");
  const humanAlertBox = document.getElementById("humanAlertBox");
  const humanReasonText = document.getElementById("humanReasonText");
  const companyValue = document.getElementById("companyValue");
  const nextStepValue = document.getElementById("nextStepValue");
  const summaryValue = document.getElementById("summaryValue");
  const keyDataContainer = document.getElementById("keyDataContainer");
  const missingDataContainer = document.getElementById("missingDataContainer");
  const replyDraftValue = document.getElementById("replyDraftValue");
  const copyReplyBtn = document.getElementById("copyReplyBtn");
  const copyBtnText = document.getElementById("copyBtnText");

  // Подстановка тестовых сценариев в поля формы
  function setPreset(testKey) {
    if (window.TEST_INQUIRIES && window.TEST_INQUIRIES[testKey]) {
      const preset = window.TEST_INQUIRIES[testKey];
      if (typeof preset === "object") {
        if (clientName) clientName.value = preset.name || "";
        if (clientPhone) clientPhone.value = preset.phone || "";
        if (clientCompany) clientCompany.value = preset.company || "";
        if (inquiryText) inquiryText.value = preset.text || "";
      } else {
        if (clientName) clientName.value = "";
        if (clientPhone) clientPhone.value = "";
        if (clientCompany) clientCompany.value = "";
        if (inquiryText) inquiryText.value = preset;
      }
      hideError();
      if (inquiryText) inquiryText.focus();
    }
  }

  if (preset1Btn) preset1Btn.addEventListener("click", () => setPreset("test1"));
  if (preset2Btn) preset2Btn.addEventListener("click", () => setPreset("test2"));
  if (preset3Btn) preset3Btn.addEventListener("click", () => setPreset("test3"));

  // Очистка всех полей формы
  if (clearTextBtn) {
    clearTextBtn.addEventListener("click", () => {
      if (clientName) clientName.value = "";
      if (clientPhone) clientPhone.value = "";
      if (clientCompany) clientCompany.value = "";
      if (inquiryText) inquiryText.value = "";
      if (clientName) clientName.focus();
      hideError();
    });
  }

  // Закрытие баннера ошибки
  if (closeErrorBtn) {
    closeErrorBtn.addEventListener("click", hideError);
  }

  // Переключение видимости блока анонимизированного текста
  if (toggleAnonBtn && anonymizedContentBox) {
    toggleAnonBtn.addEventListener("click", () => {
      const isHidden = anonymizedContentBox.classList.contains("hidden");
      if (isHidden) {
        anonymizedContentBox.classList.remove("hidden");
        toggleAnonBtn.textContent = "Скрыть";
      } else {
        anonymizedContentBox.classList.add("hidden");
        toggleAnonBtn.textContent = "Показать";
      }
    });
  }

  function showError(title, msg) {
    errorTitle.textContent = title;
    errorMessage.textContent = msg;
    errorBanner.classList.remove("hidden");
  }

  function hideError() {
    errorBanner.classList.add("hidden");
  }

  // Отрисовка данных в карточке
  function renderResult(data, anonymizationInfo, bitrix24, anonymizedText) {
    // 0. Индикатор анонимизации персональных данных
    if (privacyAlertBox && privacyAlertText) {
      if (anonymizationInfo && anonymizationInfo.detected_count > 0) {
        const count = anonymizationInfo.detected_count;
        const types = (anonymizationInfo.detected_types || []).join(", ");
        privacyAlertText.textContent = `Обнаружено и защищено персональных данных: ${count} (${types}). Данные были скрыты перед отправкой в AI и восстановлены в карточке.`;
        privacyAlertBox.classList.remove("hidden");
      } else {
        privacyAlertBox.classList.add("hidden");
      }
    }

    // 0.1 Модуль анонимизированного текста для нейросети
    if (anonymizedModule && anonymizedTextValue) {
      if (anonymizedText) {
        anonymizedTextValue.textContent = anonymizedText;
        anonymizedModule.classList.remove("hidden");
        if (anonymizedContentBox) anonymizedContentBox.classList.remove("hidden");
        if (toggleAnonBtn) toggleAnonBtn.textContent = "Скрыть";
      } else {
        anonymizedModule.classList.add("hidden");
      }
    }

    // 0.1 Информационный блок Битрикс24 CRM
    if (b24AlertBox) {
      if (bitrix24 && bitrix24.success && bitrix24.lead_id) {
        b24AlertBox.classList.remove("hidden");
        b24StatusBadge.textContent = `Лид #${bitrix24.lead_id} создан`;
        b24StatusBadge.style.background = "rgba(16, 185, 129, 0.2)";
        b24StatusBadge.style.color = "#34d399";
        b24StatusBadge.style.borderColor = "rgba(16, 185, 129, 0.35)";

        if (b24LeadLink) {
          b24LeadLink.href = bitrix24.lead_url || "#";
          b24LeadLink.classList.remove("hidden");
        }

        if (bitrix24.task_id && bitrix24.task_url) {
          if (b24TaskLink) {
            b24TaskLink.href = bitrix24.task_url;
            b24TaskLink.innerHTML = `<span>Срочная задача #${bitrix24.task_id}</span> ↗`;
            b24TaskLink.classList.remove("hidden");
          }
          if (b24Description) {
            b24Description.textContent = "Заявка успешно экспортирована в CRM: создан Лид и поставлена срочная задача ответственному менеджеру.";
          }
        } else {
          if (b24TaskLink) {
            b24TaskLink.classList.add("hidden");
          }
          if (b24Description) {
            b24Description.textContent = "Заявка успешно экспортирована в CRM Битрикс24 (создан Лид и отправлено уведомление).";
          }
        }
      } else if (bitrix24 && bitrix24.error) {
        b24AlertBox.classList.remove("hidden");
        b24StatusBadge.textContent = "Ошибка CRM";
        b24StatusBadge.style.background = "rgba(239, 68, 68, 0.2)";
        b24StatusBadge.style.color = "#f87171";
        b24StatusBadge.style.borderColor = "rgba(239, 68, 68, 0.35)";
        if (b24Description) b24Description.textContent = `Не удалось передать в Битрикс24: ${bitrix24.error}`;
        if (b24LeadLink) b24LeadLink.classList.add("hidden");
        if (b24TaskLink) b24TaskLink.classList.add("hidden");
      } else {
        b24AlertBox.classList.add("hidden");
      }
    }

    // 1. Тип лида
    const leadType = (data.lead_type || "неясно").toLowerCase();
    leadTypeBadge.className = "badge";
    if (leadType.includes("целев") && !leadType.includes("нецелев")) {
      leadTypeBadge.textContent = "Целевой запрос";
      leadTypeBadge.classList.add("badge-target");
    } else if (leadType.includes("нецелев")) {
      leadTypeBadge.textContent = "Нецелевой";
      leadTypeBadge.classList.add("badge-nontarget");
    } else {
      leadTypeBadge.textContent = "Неясно / Требует уточнения";
      leadTypeBadge.classList.add("badge-unclear");
    }

    // 2. Требуется ли человек
    const needsHuman = Boolean(data.needs_human === true || String(data.needs_human).toLowerCase() === "true");
    needsHumanBadge.className = "badge";
    if (needsHuman) {
      needsHumanBadge.textContent = "⚠️ Требуется менеджер";
      needsHumanBadge.classList.add("badge-human-yes");

      humanReasonText.textContent = data.human_reason || "Причина не детализирована";
      humanAlertBox.classList.remove("hidden");
    } else {
      needsHumanBadge.textContent = "✓ AI-обработка (без эскалации)";
      needsHumanBadge.classList.add("badge-human-no");
      humanAlertBox.classList.add("hidden");
    }

    // 3. Компания и следующий шаг
    companyValue.textContent = data.company || "Не указано";
    nextStepValue.textContent = data.next_step || "Уточнить детали заказа";

    // 4. Суть запроса
    summaryValue.textContent = data.summary || "Не указана";

    // 5. Известные параметры (key_data)
    keyDataContainer.innerHTML = "";
    if (data.key_data && typeof data.key_data === "object" && !Array.isArray(data.key_data)) {
      const keys = Object.keys(data.key_data);
      if (keys.length === 0) {
        keyDataContainer.innerHTML = '<span class="field-text">Нет выделенных параметров</span>';
      } else {
        keys.forEach((key) => {
          const val = data.key_data[key];
          const itemEl = document.createElement("div");
          itemEl.className = "key-data-item";
          itemEl.innerHTML = `
            <span class="key-data-name">${escapeHtml(key)}</span>
            <span class="key-data-val">${escapeHtml(String(val))}</span>
          `;
          keyDataContainer.appendChild(itemEl);
        });
      }
    } else if (typeof data.key_data === "string") {
      keyDataContainer.innerHTML = `<span class="field-text">${escapeHtml(data.key_data)}</span>`;
    } else {
      keyDataContainer.innerHTML = '<span class="field-text">Параметры не извлечены</span>';
    }

    // 6. Недостающие данные (missing_data)
    missingDataContainer.innerHTML = "";
    let missingList = [];
    if (Array.isArray(data.missing_data)) {
      missingList = data.missing_data.filter((item) => item && item.trim());
    } else if (typeof data.missing_data === "string" && data.missing_data.trim()) {
      missingList = [data.missing_data];
    }

    if (missingList.length === 0 || (missingList.length === 1 && missingList[0].toLowerCase().includes("нет"))) {
      const noMissingEl = document.createElement("span");
      noMissingEl.className = "missing-tag-none";
      noMissingEl.textContent = "✓ Все ключевые данные указаны";
      missingDataContainer.appendChild(noMissingEl);
    } else {
      missingList.forEach((item) => {
        const tag = document.createElement("span");
        tag.className = "missing-tag";
        tag.innerHTML = `❓ ${escapeHtml(item)}`;
        missingDataContainer.appendChild(tag);
      });
    }

    // 7. Черновик ответа
    replyDraftValue.textContent = data.reply_draft || "Черновик ответа не сформирован";

    // Переключаем отображение
    emptyState.classList.add("hidden");
    loadingState.classList.add("hidden");
    resultCard.classList.remove("hidden");
  }

  // Обработка кнопки "Обработать заявку"
  processBtn.addEventListener("click", async () => {
    const name = (clientName ? clientName.value : "").trim();
    const phone = (clientPhone ? clientPhone.value : "").trim();
    const company = (clientCompany ? clientCompany.value : "").trim();
    const text = (inquiryText ? inquiryText.value : "").trim();

    if (!name && !phone && !company && !text) {
      showError(
        "Форма не заполнена",
        "Пожалуйста, введите имя, телефон или текст обращения, либо выберите один из готовых сценариев выше."
      );
      if (inquiryText) inquiryText.focus();
      return;
    }

    hideError();
    emptyState.classList.add("hidden");
    resultCard.classList.add("hidden");
    loadingState.classList.remove("hidden");
    processBtn.disabled = true;

    try {
      const response = await fetch("/api/process", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ name, phone, company, text })
      });

      const json = await response.json();

      if (!response.ok || !json.success) {
        throw new Error(json.error || `Ошибка сервера: ${response.status}`);
      }

      renderResult(json.data, json.anonymization_info, json.bitrix24, json.anonymized_text);
    } catch (err) {
      loadingState.classList.add("hidden");
      emptyState.classList.remove("hidden");
      showError("Не удалось обработать заявку", err.message || "Неизвестная ошибка связи с сервером.");
    } finally {
      processBtn.disabled = false;
    }
  });

  // Копирование черновика ответа в буфер обмена
  if (copyReplyBtn) {
    copyReplyBtn.addEventListener("click", async () => {
      const textToCopy = replyDraftValue.textContent;
      if (!textToCopy) return;

      try {
        await navigator.clipboard.writeText(textToCopy);
        const originalText = copyBtnText.textContent;
        copyBtnText.textContent = "Скопировано!";
        copyReplyBtn.style.background = "rgba(16, 185, 129, 0.25)";
        copyReplyBtn.style.borderColor = "rgba(16, 185, 129, 0.4)";

        setTimeout(() => {
          copyBtnText.textContent = originalText;
          copyReplyBtn.style.background = "";
          copyReplyBtn.style.borderColor = "";
        }, 2000);
      } catch (err) {
        // Fallback для устаревших окружений
        const textarea = document.createElement("textarea");
        textarea.value = textToCopy;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
        copyBtnText.textContent = "Скопировано!";
        setTimeout(() => {
          copyBtnText.textContent = "Скопировать ответ";
        }, 2000);
      }
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.innerText = str;
    return div.innerHTML;
  }
});
