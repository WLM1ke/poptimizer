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

После обновление необходимо пересобрать frontend

```bash
task build
```

## Портфель

При первом запуске в портфеле будут доступны все акции и фонды торгуемые на `MOEX` с достаточной для построения моделей историей. В дальнем список доступных бумаг будет меняться на основании следующих факторов:

- Включения и исключения ценных бумаг из перечня торгуемых на `MOEX`
- Изменения требования к минимальной истории котировок для построения моделей
- Изменения требования к минимальной ликвидности ценных бумаг в зависимости от размера портфеля - чем крупнее портфель, тем меньше бумаг будет доступно

Бумаги, которые не удовлетворяют одному из требований будут автоматически исключаться при ежедневном обновлении данных, если по ним отсутствует позиция на всех счетах

На уровне портфеля отслеживается информация о характерной частоте сделок, которая используется для построения моделей и учета издержек в предложениях по оптимизации. Первоначально она установлена на уровне 1 месяца (21 торговый день)

## Дивиденды

При первоначальном запуске формируется база с дивидендами для наиболее ликвидных бумаг, которые реально торговать при портфеле от 200М.
Если у вас менее крупный портфель, необходимо заполнить информацию по остальным акциям. При дальнейшей работе будут поступать сообщения в телеграм о необходимости обновления дивидендов

## Техническая документация

Программа использует event-driven архитектуру. При запуске приложения публикуется событие `AppStarted`. На событие реагируют два обработчика:

- `BackupHandler`, который создает первоначальные данные о дивидендах в `MongoDB` при первом запуске и осуществляет их бекап при последующих
- `DataHandler` отслеживает появление новых данных на `MOEX ISS`. В случае необходимости публикует событие `NewDataPublished` с информацией о последнем торговом дне, которое запускает цикл обновления данных (синий на схеме). Если новых данных нет, то обработчик проверяет не изменился ли состав портфеля в результате действий пользователя и публикует событие `DataChecked` с информацией о последнем торговом дне и версии портфеля, которое запускает цикл тренировки моделей и обновления прогнозов (зеленый на схеме). Оба цикла завершаются отправкой сообщений для обработчика `DataHandler` в результате процесс продолжается бесконечно - или обновляются данные, или тренируются новые модели и обновляются прогнозы

![Схема событий](docs/.excalidraw.svg)

## Известные проблемы

При использовании `MPS` в `PyTorch` течет память - судя по косвенным признакам это внутренняя проблема `PyTorch`. Хочется дождаться следующей версии `PyTorch` и посмотреть не решится ли в ней проблема утечки памяти. Если не решится, постараюсь переписать блок обучения в отдельном процессе, который будет завершаться после каждого обучения. Пока есть два решения:

- перезапускать программу раз в сутки (по моему опыту на сутки памяти хватает)
- временно закомментировать условие выбора [MPS](https://github.com/WLM1ke/poptimizer/blob/master/poptimizer/use_cases/dl/trainer.py#L64), что ликвидирует утечку, но приведет к существенному замедлению обучения моделей
