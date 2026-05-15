## 📖 Примеры использования

### 1. Отправка пульта управления (Action)
Используйте этот код в любой автоматизации, чтобы отправить интерактивное меню с кнопками. Обратите внимание, что кнопки могут быть разных типов: `callback` (скрытая отправка данных) и `text` (отправка текста в чат).

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
action: vk_notify.send_message
data:
  entity_id: notify.vk_notify_2000001234
  message: "Выберите устройство:"
  keyboard:
    inline: true
    buttons:
      - - action:
            type: callback
            label: "Свет: Гостиная 💡"
            payload: '{"action": "toggle", "item": "light.living_room"}'
          color: primary
        - action:
            type: callback
            label: "Все выключить 🌑"
            payload: '{"action": "all_off"}'
          color: negative
      - - action:
            type: text
            label: "/status"
          color: secondary
```

</details>

### 2. Продвинутая клавиатура (Цвета и ссылки)
Пример отправки сразу двух сообщений: одно с разноцветными кнопками, а второе — с кнопкой типа `open_link`, которая открывает нужный URL-адрес без отправки сообщений боту.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "Пульт управления светом и картой"
description: "Отправка сообщений с разными типами кнопок"
mode: single
actions:
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: "🎛 Пульт управления светом:"
      keyboard:
        inline: true
        buttons:
          - - action:
                type: callback
                label: "Переключить свет 💡"
                payload: '{"action": "toggle_light"}'
              color: primary
          - - action:
                type: callback
                label: "Включить всё ☀️"
                payload: '{"action": "all_on"}'
              color: positive
            - action:
                type: callback
                label: "Выключить всё 🌑"
                payload: '{"action": "all_off"}'
              color: negative
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: "Нажми на кнопку, чтобы увидеть объект на карте:"
      keyboard:
        inline: true
        buttons:
          - - action:
                type: open_link
                link: "[https://yandex.ru/maps/?pt=37.62,55.75&z=15&l=map](https://yandex.ru/maps/?pt=37.62,55.75&z=15&l=map)"
                label: "Открыть карту 📍"
```

</details>

### 3. Обработка нажатий (Trigger)
Эта автоматизация «слушает» невидимые нажатия `callback`-кнопок из примеров выше и выполняет действия в Home Assistant на основе данных из поля `payload`.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Обработка кнопок пульта"
description: "Реагирует на нажатия callback-кнопок из ВК"
mode: parallel
triggers:
  - trigger: event
    event_type: vk_notify_callback
    event_data:
      peer_id: 2000001234  # <--- Фильтр: реагировать только на нажатия в этом чате
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.payload.action == 'toggle_light' }}"
        sequence:
          - action: light.toggle
            target:
              entity_id: light.double_switch_2_2_3
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.payload.action == 'all_off' }}"
        sequence:
          - action: light.turn_off
            target:
              entity_id: all
```

</details>

### 4. Реакция на текстовые команды
Если вы нажали кнопку типа `text` или просто написали в чат сообщение со слэшем (например, `/status`), Home Assistant сгенерирует событие `vk_notify_command`. Вот как на него ответить:

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Реакция на текстовые команды"
description: "Отвечает на команду /status"
mode: single
triggers:
  - trigger: event
    event_type: vk_notify_command
    event_data:
      command: status  # <--- Указываем команду без слэша
      peer_id: 2000001234
actions:
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: "🟢 Все системы работают в штатном режиме!"
```

</details>

### 5. Умный пульт (Единая автоматизация с динамическим обновлением)
Эта мощная автоматизация объединяет всё: она отправляет пульт по команде `/пульт`, а при нажатии на кнопку — переключает свет и **редактирует само сообщение**, меняя цвет кнопки (зеленый/красный) в зависимости от текущего статуса устройства.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Умный пульт (Единая автоматизация)"
description: "Вызов пульта и динамическое обновление кнопок в одном месте"
mode: parallel
max: 10
triggers:
  # Триггер 1: Пользователь написал /пульт
  - trigger: event
    event_type: vk_notify_command
    event_data:
      command: пульт
      peer_id: 2000001234
    id: call_remote

  # Триггер 2: Пользователь нажал невидимую кнопку callback
  - trigger: event
    event_type: vk_notify_callback
    event_data:
      peer_id: 2000001234
    id: button_pressed

actions:
  - choose:
      # ВЕТКА 1: Отправка нового пульта в чат
      - conditions:
          - condition: trigger
            id: call_remote
        sequence:
          - action: vk_notify.send_message
            data:
              entity_id: notify.vk_notify_2000001234
              message: "🎛 **Главный пульт управления**"
              keyboard:
                inline: true
                buttons:
                  - - action:
                        type: callback
                        label: >-
                          {% if is_state('light.double_switch_2_2_3', 'on') %}Выключить свет 🌑
                          {% else %}Включить свет 💡{% endif %}
                        payload: '{"action": "toggle_light"}'
                      color: >-
                        {% if is_state('light.double_switch_2_2_3', 'on') %}negative
                        {% else %}positive{% endif %}

      # ВЕТКА 2: Обработка нажатий и обновление сообщения
      - conditions:
          - condition: trigger
            id: button_pressed
        sequence:
          - choose:
              - conditions:
                  - condition: template
                    value_template: "{{ trigger.event.data.payload.action == 'toggle_light' }}"
                sequence:
                  # 1. Переключаем свет
                  - action: light.toggle
                    target:
                      entity_id: light.double_switch_2_2_3
                  
                  # 2. Ждем секунду для обновления статуса в HA
                  - delay: "00:00:01"
                  
                  # 3. Редактируем сообщение (меняем цвет и текст)
                  - action: vk_notify.edit_message
                    data:
                      entity_id: notify.vk_notify_2000001234
                      conversation_message_id: "{{ trigger.event.data.conversation_message_id }}"
                      message: "🎛 **Главный пульт управления**"
                      keyboard:
                        inline: true
                        buttons:
                          - - action:
                                type: callback
                                label: >-
                                  {% if is_state('light.double_switch_2_2_3', 'on') %}Выключить свет 🌑
                                  {% else %}Включить свет 💡{% endif %}
                                payload: '{"action": "toggle_light"}'
                              color: >-
                                {% if is_state('light.double_switch_2_2_3', 'on') %}negative
                                {% else %}positive{% endif %}
```

</details>

### 6. Удаление сообщения по кнопке (Закрыть пульт)
Пример того, как можно добавить на пульт кнопку "Закрыть ❌", которая будет физически удалять сообщение из истории чата.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Закрытие пульта"
description: "Удаляет сообщение с пультом при нажатии на кнопку закрытия"
triggers:
  - trigger: event
    event_type: vk_notify_callback
    event_data:
      peer_id: 2000001234
actions:
  - choose:
      - conditions:
          - condition: template
            # Предполагается, что на пульте есть кнопка с payload: '{"action": "close_remote"}'
            value_template: "{{ trigger.event.data.payload.action == 'close_remote' }}"
        sequence:
          - action: vk_notify.delete_message
            data:
              entity_id: notify.vk_notify_2000001234
              # Берем ID сообщения прямо из клика по кнопке
              conversation_message_id: "{{ trigger.event.data.conversation_message_id }}"
```

</details>

### 7. Удаление и редактирование отправленных сообщений (Самоуничтожающиеся сообщения)

Интеграция поддерживает два способа получить `message_id` только что отправленного сообщения. Выбирайте тот, который больше подходит для вашей задачи.

#### Способ 1: Быстрый (Через глобальный атрибут)
Интеграция автоматически сохраняет ID **самого последнего** отправленного сообщения в атрибут `last_message_id`. Это очень удобно для быстрых автоматизаций.

⚠️ **ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:** Используйте этот способ **только для мгновенных действий** или коротких задержек (до пары минут). Если вы поставите таймер на 1 час, и за это время бот отправит в чат *другое* уведомление (например, сработает датчик), атрибут перезапишется. В итоге скрипт удалит не то сообщение!

<details>
  <summary><b>👨‍💻 Показать код (Быстрый способ)</b></summary>

```yaml
alias: "VK: Быстрое удаление"
actions:
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: "⏳ Завариваю кофе..."
      
  - delay: "00:00:05" # Короткая задержка безопасна
  
  - action: vk_notify.delete_message
    data:
      entity_id: notify.vk_notify_2000001234
      # Просто берем ID из атрибута:
      message_id: "{{ state_attr('notify.vk_notify_2000001234', 'last_message_id') }}"
```
</details>

#### Способ 2: Надежный пуленепробиваемый таймер (Service Response)
Для долгих задержек (например, удалить сообщение о стирке через час) обязательно используйте локальные переменные `response_variable`. В этом случае автоматизация "запоминает" ID именно своего сообщения и не зависит от того, сколько еще уведомлений отправит бот за этот час.

<details>
  <summary><b>👨‍💻 Показать код (Надежный способ)</b></summary>

```yaml
alias: "VK: Надежный таймер (1 час)"
actions:
  # 1. Отправляем и кладем ответ ВК в локальную переменную sent_result
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: "👕 Стиральная машина закончила стирку!"
    response_variable: sent_result
    
  # 2. Ждем 1 час. (За это время бот может писать в чат что угодно - это безопасно).
  - delay: "01:00:00"
  
  # 3. Достаем ID ИМЕННО ЭТОГО сообщения из сохраненной переменной и удаляем
  - variables:
      bot_msg_id: "{{ (sent_result.values() | first | default({})).get('message_id', 0) | int }}"
  - if:
      - condition: template
        value_template: "{{ bot_msg_id > 0 }}"
    then:
      - action: vk_notify.delete_message
        data:
          entity_id: notify.vk_notify_2000001234
          message_id: "{{ bot_msg_id }}"

```

</details>

### 8. Пинг-Понг (Ответ на конкретное сообщение)
Простая автоматизация для проверки связи. Бот реагирует на команды «/пинг» «/ping» в чате и отправляет ответ, цитируя (реплая) исходное сообщение пользователя через параметр `reply_to`.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK Тест 5: Реплай (Пинг-Понг)"
description: Бот отвечает только на команду /пинг или /ping в любом регистре
mode: parallel
trigger:
  - platform: event
    event_type: vk_notify_command
    event_data:
      entity_id: notify.vk_notify_2000000003
condition:
  - condition: template
    value_template: >-
      {{ trigger.event.data.get('command', '') | lower in ['пинг', 'ping'] }}
action:
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000000003
      message: 🏓 Понг! Бот на связи и умеет отвечать на сообщения.
      reply_to: "{{ trigger.event.data.get('conversation_message_id') }}"
```

</details>

### 9. Шпион (Проверка статуса по заданному ID)
Возвращает имя, статус онлайна и время последнего визита пользователя по жестко заданному `user_id`. Используется сервис `get_user_info`, возвращающий данные через `response_variable`.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK Тест 3: Шпион (Проверка онлайна выбранного пользователя)"
description: "Возвращает имя, статус онлайна и время визита по жестко заданному ID"
mode: parallel
triggers:
  - trigger: event
    event_type: vk_notify_command
conditions:
  - condition: template
    value_template: >-
      {{ 'онлайн' in trigger.event.data.get('command', '') | lower or 'онлайн'
      in trigger.event.data.get('text', '') | lower }}
actions:
  - action: vk_notify.get_user_info
    data:
      entity_id: notify.vk_notify_2000001234
      user_id: "1234567"  # замените на нужный VK ID
    response_variable: vk_user
  - variables:
      info: "{{ vk_user.values() | first | default({}) }}"
      is_online: "{{ info.get('is_online', false) }}"
      status_text: "{{ '🟢 В сети' if is_online else '⚫ Не в сети' }}"
      ts: "{{ info.get('last_seen', 0) | int }}"
      last_seen_text: |-
        {% if is_online %}
          Прямо сейчас!
        {% elif ts > 0 %}
          {{ ts | timestamp_custom('%d.%m.%Y в %H:%M', true) }}
        {% else %}
          Скрыто настройками приватности
        {% endif %}
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: |
        🕵️‍♂️ **Досье пользователя:**
        👤 Имя: {{ info.get('full_name', 'Неизвестно') }}
        📱 Статус: {{ status_text }}
        🕒 Был(а) в сети: {{ last_seen_text }}
      reply_to: "{{ trigger.event.data.get('conversation_message_id', 0) }}"
```

</details>

### 10. Динамический Шпион (Кто написал команду?)
Улучшенная версия «Шпиона». Бот автоматически определяет статус того человека, который отправил команду, используя `from_id` из данных события.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK Тест 3: Шпион (Динамический с временем)"
mode: parallel
triggers:
  - trigger: event
    event_type: vk_notify_command
conditions:
  - condition: template
    value_template: "{{ 'онлайн' in trigger.event.data.get('command', '') | lower }}"
actions:
  - action: vk_notify.get_user_info
    data:
      entity_id: notify.vk_notify_2000001234
      user_id: "{{ trigger.event.data.from_id }}"
    response_variable: vk_user
  - variables:
      info: "{{ vk_user.values() | first | default({}) }}"
      is_online: "{{ info.get('is_online', false) }}"
      status: "{{ '🟢 В сети' if is_online else '⚫ Не в сети' }}"
      ts: "{{ info.get('last_seen', 0) | int }}"
      last_seen_text: |-
        {% if is_online %}
          Прямо сейчас!
        {% elif ts > 0 %}
          {{ ts | timestamp_custom('%d.%m.%Y в %H:%M', true) }}
        {% else %}
          Скрыто настройками приватности
        {% endif %}
  - action: vk_notify.send_message
    data:
      entity_id: notify.vk_notify_2000001234
      message: |
        🕵️‍♂️ **Результат пробива:**
        👤 Имя: {{ info.get('full_name', 'Неизвестно') }}
        📱 Статус: {{ status }}
        🕒 Был(а) в сети: {{ last_seen_text }}
      reply_to: "{{ trigger.event.data.conversation_message_id | default(0) }}"
```

</details>

### 11. Двусторонняя связь (Тестовый пример)
Наглядная автоматизация для проверки событий `vk_notify_typing` (набор текста) и `vk_notify_read` (прочтение). 

⚠️ **ВАЖНОЕ ОГРАНИЧЕНИЕ VK API:** События о прочтении сообщений (`vk_notify_read`) работают **только в личных диалогах с ботом**. ВКонтакте не отправляет ботам статусы прочтения из общих бесед. Тестируйте эту автоматизацию в диалоге тет-а-тет с вашим сообществом!

*Внимание: для реакции на «прочтение» мы специально используем внутреннее уведомление Home Assistant (`persistent_notification`), чтобы не создать бесконечную петлю в ВК (бот пишет -> вы читаете -> бот снова пишет).*

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK Тест 6: Двусторонняя связь (Тайпинг и Прочтение)"
description: >-
  Демонстрация реакции бота на ваши действия в чате (только для личных
  сообщений)
mode: single
triggers:
  - trigger: event
    event_type: vk_notify_typing
    id: typing
  - trigger: event
    event_type: vk_notify_read
    id: read
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: typing
        sequence:
          - action: vk_notify.send_message
            data:
              entity_id: notify.vk_notify_2000000008 # <-- Ваш личный VK ID(Бота), а не ID чата!
              message: 👀 О, вижу, ты что-то печатаешь! Жду команду...
          - delay: "00:00:10"
      
      # --- ВЕТКА 2: ЧТО ДЕЛАТЬ, ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПРОЧИТАЛ ---
      - conditions:
          - condition: trigger
            id: read
        sequence:
          # Отправляем уведомление в панель самого Home Assistant (колокольчик слева внизу)
          - action: persistent_notification.create
            data:
              title: "ВКонтакте (VK Notify)"
              message: "Пользователь только что прочитал ваши сообщения! ✔️✔️"
          - delay: "00:00:10"
```

</details>

### 12. Всё в одном (все возможности в одной автоматизации)
Автоматизация демонстратор всех возможностей данного форка. Не забудьте изменить id 2000000003 на свои, а во втором блоке помимо этого задайте ID искомого пользователя VK для определения Имени и Фамилии.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Демонстрация всех возможностей (Master Showcase) V3"
description: "Полный прогон всех служб обновленной интеграции VK Notify, включая парсеры и get_user_info"
mode: single
triggers: [] # Запускается вручную для тестов

actions:
  # ==========================================
  # 1. ИМИТАЦИЯ АКТИВНОСТИ
  # ==========================================
  - alias: "1. Имитация набора текста (Печатает...)"
    action: vk_notify.set_activity
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      type: typing
  - delay: "00:00:02"

  # ==========================================
  # 2. ПОЛУЧЕНИЕ ДАННЫХ ПОЛЬЗОВАТЕЛЯ
  # ==========================================
  - alias: "2. Скрытый запрос данных пользователя (get_user_info)"
    action: vk_notify.get_user_info
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      user_id: "123456789" # ID Пользователя ВК <------------------
    response_variable: vk_user

  # ==========================================
  # 3. БАЗОВОЕ СООБЩЕНИЕ + ИМЯ + RESPONSE VARIABLE
  # ==========================================
  - alias: "3. Отправка приветствия по имени и сохранение ID сообщения"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      title: "🚀 ТЕСТОВЫЙ ПРОГОН СИСТЕМЫ"
      message: >
        <b>Приветствую, {{ vk_user.full_name }}!</b> 👋
        
        Статус в ВК: {{ '✅ В сети' if vk_user.is_online else '❌ Не в сети' }}
        Система обновлена до энтерпрайз-уровня. Начинаю демонстрацию функций!
      parse_mode: html
      keyboard:
        inline: true
        buttons:
          - - action:
                type: callback
                label: "👍 Круто!"
                payload: '{"test":"ok"}'
              color: positive
    response_variable: welcome_msg
  - delay: "00:00:02"

  # ==========================================
  # 4. ДЕМОНСТРАЦИЯ ВСЕХ РЕЖИМОВ ПАРСИНГА (PARSE_MODE)
  # ==========================================

  # 4.1. Режим: HTML (По умолчанию)
  - alias: "4.1. Тест парсера: HTML (По умолчанию)"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: >
        🌐 <b>Тест режима HTML:</b>
        Здесь работает <i>курсив</i>, <u>подчеркивание</u>, <a href="https://ha.ru">гиперссылки</a> 
        и, конечно же, <b>жирный</b> шрифт!
      parse_mode: html
  - delay: "00:00:02"

  # 4.2. Режим: Markdown (Устаревший)
  - alias: "4.2. Тест парсера: Markdown (Legacy)"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: >
        📝 **Тест режима Markdown (Legacy):**
        Здесь работает *курсив*, [гиперссылки](https://ha.ru) 
        и, конечно же, **жирный** шрифт!
      parse_mode: markdown
  - delay: "00:00:02"

  # 4.3. Режим: MarkdownV2
  - alias: "4.3. Тест парсера: MarkdownV2"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: >
        🚀 **Тест режима MarkdownV2:**
        Здесь работает *курсив*, __подчеркивание__, [гиперссылки](https://ha.ru) 
        и, конечно же, **жирный** шрифт!
        (Спецсимволы \- \. \! \+ передаются корректно).
      parse_mode: markdownv2
  - delay: "00:00:02"

  # 4.4. Режим: Обычный текст (Plain)
  - alias: "4.4. Тест парсера: Plain (Обычный текст)"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: >
        🧱 Тест режима Plain (Обычный текст):
        Теги <b>HTML</b> и **Markdown** теперь будут отображаться как обычные символы.
        Смотри: <b>жирный</b> или **жирный** больше не работают, текст идет как есть.
        Идеально для логов: error_system_log_2026.txt
      parse_mode: plain
  - delay: "00:00:02"

  # ==========================================
  # 5. ОТПРАВКА СТИКЕРА
  # ==========================================
  - alias: "5. Отправка стикера ВК"
    action: vk_notify.send_sticker
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      sticker_id: 3 # Собака Спотти
  - delay: "00:00:02"

  # ==========================================
  # 6. МАНИПУЛЯЦИЯ СООБЩЕНИЯМИ (РЕАКЦИЯ, ЗАКРЕП, РЕДАКТИРОВАНИЕ)
  # ==========================================
  
  # Ставим лайк (реакцию) на приветственное сообщение
  - alias: "6.1. Установка реакции (Лайк) на первое сообщение"
    action: vk_notify.send_reaction
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      reaction_id: 4 # Огонь 🔥
      conversation_message_id: >
        {% set r = welcome_msg.values() | first | default({}) %}
        {{ r.get('conversation_message_id', 0) }}
  
  # Закрепляем это сообщение
  - alias: "6.2. Закрепление первого сообщения в шапке чата"
    action: vk_notify.pin_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      conversation_message_id: >
        {% set r = welcome_msg.values() | first | default({}) %}
        {{ r.get('conversation_message_id', 0) }}

  # Редактируем текст первого сообщения
  - alias: "6.3. Редактирование текста первого сообщения"
    action: vk_notify.edit_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: "<b>✅ Данные {{ vk_user.full_name }} получены.</b> Тест продолжается..."
      parse_mode: html
      conversation_message_id: >
        {% set r = welcome_msg.values() | first | default({}) %}
        {{ r.get('conversation_message_id', 0) }}
  - delay: "00:00:02"

  # ==========================================
  # 7. ГЕОЛОКАЦИЯ (КАРТА)
  # ==========================================
  - alias: "7. Отправка геолокации (Координаты Кремля)"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: "📍 Координаты (Московский Кремль):"
      lat: "55.7520"
      long: "37.6175"
  - delay: "00:00:02"

  # ==========================================
  # 8. ФОТО ИЗ ИНТЕРНЕТА (ПО URL)
  # ==========================================
  - alias: "8. Отправка картинки по ссылке (URL)"
    action: vk_notify.send_photo
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      url: "[https://www.home-assistant.io/images/default-social.png](https://www.home-assistant.io/images/default-social.png)"
      message: "📸 Отправка картинки напрямую по ссылке URL."
      parse_mode: html
  - delay: "00:00:02"

  # ==========================================
  # 9. КАРУСЕЛЬ (ШАБЛОН)
  # ==========================================
  - alias: "9. Отправка карусели с использованием имени пользователя"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: "🎠 Тест карусели:"
      template:
        type: carousel
        elements:
          - title: "Элемент 1"
            description: "Привет, {{ vk_user.full_name }}!"
            buttons:
              - action:
                  type: callback
                  label: "Кнопка 1"
                  payload: '{"test":"1"}'
                color: primary
          - title: "Элемент 2"
            description: "Статус ВК: {{ 'В сети' if vk_user.is_online else 'Оффлайн' }}"
            buttons:
              - action:
                  type: callback
                  label: "Кнопка 2"
                  payload: '{"test":"2"}'
                color: positive
  - delay: "00:00:02"

  # ==========================================
  # 10. ИЗМЕНЕНИЕ НАЗВАНИЯ ЧАТА (ТРЕБУЮТСЯ ПРАВА АДМИНА)
  # ==========================================
  - alias: "10. Изменение названия беседы/чата (нужны права Администратора)"
    action: vk_notify.edit_chat
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      title: "🟢 ТЕСТ ЗАВЕРШЕН | Дом 190"
    continue_on_error: true # Если бот не админ, пропустит без остановки скрипта

  # ==========================================
  # 11. ФАЙЛЫ И ГОЛОСОВЫЕ (ПРИМЕРЫ ДЛЯ ЛОКАЛЬНЫХ ПУТЕЙ)
  # ==========================================
  # Раскомментируйте и укажите свои пути, когда добавите файлы в папку /config/www/
  #
  # - alias: "11.1. Статус 'Записывает голосовое...'"
  #   action: vk_notify.set_activity
  #   target: { entity_id: notify.vk_notify_2000000003 }
  #   data: { type: audiomsg }
  # - delay: "00:00:02"
  #
  # - alias: "11.2. Отправка голосового сообщения (.ogg)"
  #   action: vk_notify.send_voice
  #   target: { entity_id: notify.vk_notify_2000000003 }
  #   data:
  #     file: "/config/www/test_voice.ogg"
  #
  # - alias: "11.3. Отправка файла документа"
  #   action: vk_notify.send_file
  #   target: { entity_id: notify.vk_notify_2000000003 }
  #   data:
  #     file: "/config/www/report.pdf"
  #     message: "📄 Отчет о тестировании"

  # ==========================================
  # 12. ЗАВЕРШЕНИЕ
  # ==========================================
  - alias: "12. Завершающее сообщение"
    action: vk_notify.send_message
    target:
      entity_id: notify.vk_notify_2000000003
    data:
      message: "🏁 <b>Все системы работают штатно.</b> Тест окончен!"
      parse_mode: html
```

</details>

### 13. Пример работы интерактивных функций (Снэкбары и Открепление)
Эта автоматизация — наглядная демонстрация интерактивных фишек интеграции. В одном сценарии показана отправка сообщения, создание callback-клавиатуры, чтение ID отправленного сообщения, его закрепление, а затем — реакция на нажатие кнопки со всплывающим Снэкбаром, открепление и динамическое очищение кнопок.

<details>
  <summary><b>👨‍💻 Показать код YAML</b></summary>

```yaml
alias: "VK: Тест функций (Снэкбар и Unpin)"
description: Запустите автоматизацию вручную, чтобы получить тестовую кнопку.
mode: parallel
triggers:
  - trigger: event
    event_type: vk_notify_callback
    id: button_click
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger is not defined or trigger.id != 'button_click' }}"
        sequence:
          - action: vk_notify.send_message
            target:
              entity_id: notify.vk_notify_2000000003
            data:
              title: 🛠 Интерактивный тест
              message: >-
                Я прислал тебе кнопку. Нажми её, чтобы проверить нативные Снэкбары!


                📌 <i>Кстати, я сейчас закреплю это сообщение.</i>
              parse_mode: html
              auto_answer_callback: false # <-- Важно для корректной работы Снэкбара
              keyboard:
                inline: true
                buttons:
                  - - action:
                        type: callback
                        label: 🪄 Испытать магию!
                        payload: "{\"action\": \"test_new_features\"}"
                      color: positive
            response_variable: test_msg
          - delay: "00:00:02"
          - action: vk_notify.pin_message
            target:
              entity_id: notify.vk_notify_2000000003
            data:
              conversation_message_id: >
                {% set r = test_msg.values() | first | default({}) %} {{
                r.get('conversation_message_id', 0) }}
      - conditions:
          - condition: trigger
            id: button_click
          - condition: template
            value_template: >-
              {% set p = trigger.event.data.payload | default({}) %} {% set
              payload_data = p | from_json if p is string else p %} {{
              payload_data.get('action') == 'test_new_features' }}
        sequence:
          - action: vk_notify.answer_callback
            target:
              entity_id: notify.vk_notify_2000000003
            data:
              event_id: "{{ trigger.event.data.event_id }}"
              user_id: "{{ trigger.event.data.user_id }}"
              message: 🚀 Магия работает! Сообщение откреплено.
          - action: vk_notify.unpin_message
            target:
              entity_id: notify.vk_notify_2000000003
            data:
              conversation_message_id: "{{ trigger.event.data.conversation_message_id }}"
          - action: vk_notify.edit_message
            target:
              entity_id: notify.vk_notify_2000000003
            data:
              conversation_message_id: "{{ trigger.event.data.conversation_message_id }}"
              message: |-
                ✅ <b>Тест успешно завершен!</b>

                Вы увидели снэкбар, а это сообщение пропало из закрепа чата.
              parse_mode: html
              keyboard:
                inline: true
                buttons: []
```
</details>

---

## ✨ Базовые возможности (Шпаргалка по службам)

<details>
  <summary><b>📖 Как вызывать отдельные службы в YAML</b></summary>
  
#### 1. Имитация бурной деятельности («Бот печатает...»)
Отлично подходит для скриптов, которые парсят данные или ждут ответа от аппаратуры. Бот будет показывать статус активности в течение 10 секунд.

```yaml
action: vk_notify.set_activity
data:
  entity_id: notify.vk_notify_2000001234
  type: typing # или 'audiomsg', если бот "записывает голосовое"
```

#### 2. Реакции (Лайки) на сообщения
Чтобы бот не засорял чат ответами "ОК, выключил", он может просто поставить лайк на вашу команду. 
*(Коды реакций VK: 1 = 👍, 2 = 👎, 3 = ❤️, 4 = 🔥 и т.д.)*

```yaml
action: vk_notify.send_reaction
data:
  entity_id: notify.vk_notify_2000001234
  conversation_message_id: "{{ trigger.event.data.conversation_message_id }}" # ID сообщения из триггера
  reaction_id: 1 # Ставим лайк 👍
```

#### 3. Геометки (Отправка координат)
Бот пришлет интерактивную карту прямо в чат.

```yaml
action: vk_notify.send_message
data:
  entity_id: notify.vk_notify_2000001234
  message: "📍 Автомобиль припаркован здесь:"
  lat: "55.751244"
  long: "37.618423"
```

#### 4. Карусель (Шаблоны)
Отправка красивых горизонтальных карточек с кнопками.

```yaml
action: vk_notify.send_message
data:
  entity_id: notify.vk_notify_2000001234 
  message: "💡 Выберите сценарий освещения для гостиной:"
  template:
    type: carousel
    elements:
      # Карточка 1
      - title: "Вечерний отдых 🌙"
        description: "Приглушенный теплый свет (30%)"
        buttons:
          - action:
              type: callback
              label: "Включить"
              payload: '{"action": "set_scene", "scene": "evening"}'
            color: primary 
      
      # Карточка 2
      - title: "Яркий свет ☀️"
        description: "Максимальная яркость (100%)"
        buttons:
          - action:
              type: callback
              label: "Включить"
              payload: '{"action": "set_scene", "scene": "bright"}'
            color: positive 
      
      # Карточка 3
      - title: "Режим кино 🍿"
        description: "Выключить основной свет, оставить подсветку ТВ"
        buttons:
          - action:
              type: callback
              label: "Включить"
              payload: '{"action": "set_scene", "scene": "movie"}'
            color: secondary 
```

#### 5. Закрепление сообщения
Например, можно отправить главное меню с кнопками и сразу прибить его гвоздями к верху чата.

```yaml
# Сначала отправляем сообщение и получаем ответ
- action: vk_notify.send_message
  data:
    entity_id: notify.vk_notify_2000001234
    message: "🎛 Главный пульт управления домом"
    # ... тут ваша клавиатура ...
  response_variable: msg_response

# Затем закрепляем это сообщение
- action: vk_notify.pin_message
  data:
    entity_id: notify.vk_notify_2000001234
    conversation_message_id: "{{ (msg_response.values() | first).conversation_message_id }}"
```

#### 6. Голосовые сообщения
Используйте службу `send_voice`, передав ей локальный путь к аудиофайлу в формате `.ogg`.

```yaml
action: vk_notify.send_voice
data:
  entity_id: notify.vk_notify_2000001234
  file: "/config/www/audio/alarm.ogg"
```

</details>

---

<details>
  <summary><b>🖼 Скриншоты установки и настройки (Нажмите, чтобы развернуть)</b></summary>
  <br>
  <img width="584" height="722" alt="Снимок экрана 2026-04-08 в 10 24 57" src="https://github.com/user-attachments/assets/3b427935-f55f-4a38-b312-996a3b6fa1e2" />

<img width="882" height="798" alt="Снимок экрана 2026-04-08 в 10 29 28" src="https://github.com/user-attachments/assets/5f5f5ad6-a9e8-42df-97f0-8333c94df659" />

<img width="882" height="798" alt="Снимок экрана 2026-04-08 в 10 30 40" src="https://github.com/user-attachments/assets/8fc155a5-cc20-48b6-91ec-89013a3e995a" />

<img width="1011" height="840" alt="Снимок экрана 2026-04-08 в 10 27 48" src="https://github.com/user-attachments/assets/288f2258-0669-43e5-bd22-00ae36a9dcfa" />

<img width="582" height="294" alt="Снимок экрана 2026-04-08 в 16 18 00" src="https://github.com/user-attachments/assets/e77dce74-d6d8-4979-9734-74d14952a1c7" />

<img width="582" height="294" alt="Снимок экрана 2026-04-08 в 16 17 52" src="https://github.com/user-attachments/assets/4365b34d-f3d4-4761-9469-efa8d51b0f1c" />

https://github.com/user-attachments/assets/e257553f-e171-4935-a5c5-afb8dddb018f

https://github.com/user-attachments/assets/af5d2632-b4f9-4635-843e-f40ce7968589

https://github.com/user-attachments/assets/3a28f5b8-e827-4fc7-941e-62d93620b142

</details>
