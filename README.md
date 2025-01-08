# Оптимизация долгосрочного портфеля акций

## Установка

Для установки необходимо:

- заполнить `.env.template` и переименовать его в `.env`
- установить [Task](https://taskfile.dev/installation/)
- запустить команду установки необходимых инструментов

```bash
task install
```

- запустить MongoDB, которая указана в `.env`. Для локального запуска на MacOS

```bash
task mongo
```

- запустить программу

```bash
task run
```

- перейти по адресу, указанному `.env`
- добавить в настройках хотя бы один брокерский счет
- заполнить его актуальной информацией по имеющимся акциям и денежным средствам

## Обновление

После обновление необходимо пересобрать frontend и сбросить кеши в браузере

```bash
task build
```

## Портфель

При первом запуске в портфеле будут доступны все акции и фонды торгуемые на `MOEX` с достаточной для построения моделей историей. В дальнем список доступных бумаг будет меняться на основании следующих факторов:

- включения и исключения ценных бумаг из перечня торгуемых на `MOEX`
- изменения требования к минимальной истории котировок для построения моделей
- изменения требования к минимальной ликвидности ценных бумаг в зависимости от размера портфеля - чем крупнее портфель, тем меньше бумаг будет доступно

Бумаги, которые не удовлетворяют одному из требований будут автоматически исключаться при ежедневном обновлении данных, если по ним отсутствует позиция на всех счетах

На уровне портфеля отслеживается информация о характерной частоте сделок, которая используется для построения моделей и учета издержек в предложениях по оптимизации. Первоначально она установлена на уровне 1 месяца (21 торговый день)

Агрегированные данные по всем счетам выводятся на вкладке `Portfolio`, а данные по отдельным счетам с возможностью редактирования в разделах соответствующих счетов

## Дивиденды

При первоначальном запуске формируется база с дивидендами для наиболее ликвидных бумаг, которые реально торговать при портфеле от 200М.
Если у вас менее крупный портфель, необходимо заполнить информацию по остальным акциям. При дальнейшей работе будут поступать сообщения в `Telegram` о необходимости обновления дивидендов и появится возможность их редактирования разделе `Dividends`

## Модели

Используемые для построения прогнозов модели формируются автоматически с помощью эволюционного алгоритма:

- модели с большей доходностью на тестовой выборке выживают и создают новые модели с похожими характеристиками
- модели с меньшей доходностью на тестовой выборке удаляются

В качестве тестовой выборки используются последние торговые дни. Их количество постепенно увеличивается по мере работы эволюции сначала достаточно быстро с последующим замедлением. В результате бумаги с короткой историей могут быть исключены из портфеля.
Для тренировки моделей используются все ценные бумаги из текущего портфеля, а прогноз строится на несколько дней вперед в соответствии с актуальной частотой сделок

## Прогнозы и рекомендации по оптимизации

Прогнозы по всем моделям агрегируются и выводятся на вкладке `Forecast` в пересчете в годовое выражение, при этом используется портфельная теория для расчета рисков и доходности портфеля на основе характеристик отдельных позиций

На вкладке `Optimization` выводятся рекомендации о покупке и продаже ценных бумаг. При этом учитывается разброс в прогнозах - нижняя граница доверительного интервала в предложениях на покупку должна быть больше верхней границы доверительного интервала предложений на продажу с учетом транзакционных издержек

В некоторых случаях может сложиться ситуация, когда предложений по оптимизации не будет:

- при малом количестве прогнозов или большом их расхождении - больше ширина доверительных интервалов
- большой частоте сделок - больших транзакционных издержках, которые учитываются при расчете доверительных интервалов
- близости портфеля к оптимальному - все малодоходные и рискованные бумаги проданы, а у остальных не достаточно сильно различаются прогнозные метрики, чтобы перекрыть транзакционные издержки

В этом случае будет выведена одна бумага с максимальной нижней границей доверительного интервала, которую необходимо покупать при наличии свободных денежных средств

Прогноз и предложение по оптимизации пересчитывается при появлении достаточно большого количества новых моделей и с некоторой задержкой при изменении портфеля. В интерфейсе будет отображаться надпись `outdated`, если расчеты пока не обновились после последнего изменения портфеля

## Техническая информация

Frontend сделан на `TypeScript` и `SvelteKit`, а Backend на `asyncio` `Python`, в том числе:

- HTTP клиент и сервер `aiohttp`
- Хранение данных `async` `PyMongo`
- Валидация и сериализация данных `Pydantic`
- Обучения моделей `PyTorch`
- Статистические тесты и оптимизация `SciPy`

Backend использует event-driven архитектуру - сообщения публикуются в шину, которая на основании типа сообщения выбирает необходимые обработчики и запускает их выполнение. Если обработчик возвращает новые события, то они автоматически отправляются в шину

При запуске приложения публикуется событие `AppStarted`, на которое реагирует два обработчика:

- `BackupHandler`, который создает первоначальные данные о дивидендах в `MongoDB` при первом запуске и осуществляет их бекап при последующих
- `DataHandler` отслеживает появление новых данных на `MOEX ISS`. В случае необходимости публикует событие `NewDataPublished` с информацией о последнем торговом дне, которое запускает цикл обновления данных (синий на схеме). Если новых данных нет, то обработчик проверяет не изменился ли состав портфеля в результате действий пользователя и публикует событие `DataChecked` с информацией о последнем торговом дне и версии портфеля, которое запускает цикл тренировки моделей и обновления прогнозов (зеленый на схеме). Оба цикла завершаются отправкой сообщений для обработчика `DataHandler` в результате процесс продолжается бесконечно - или обновляются данные, или тренируются новые модели и обновляются прогнозы

Обработка HTTP запросов также построена на публикации запросов в шину, которая осуществляет выбор соответствующего обработчика и возврат ответа

![Схема событий](docs/.excalidraw.svg)

## Известные проблемы

При использовании `MPS` в `PyTorch` течет память - судя по косвенным признакам это внутренняя проблема `PyTorch`. Хочется дождаться следующей версии `PyTorch` и посмотреть не решится ли в ней проблема утечки памяти. Если не решится, постараюсь переписать блок обучения в отдельном процессе, который будет завершаться после каждого обучения. Пока есть два решения:

- перезапускать программу раз в сутки (по моему опыту на сутки памяти хватает)
- временно закомментировать условие выбора [MPS](https://github.com/WLM1ke/poptimizer/blob/master/poptimizer/use_cases/dl/trainer.py#L64), что ликвидирует утечку, но приведет к существенному замедлению обучения моделей
