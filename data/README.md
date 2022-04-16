# Микросервис для загрузки данных

Прототип в разработке - не используется в основном коде

## Endpoints

### api/{group}/{ticker}

Получение данных в формате MongoDB Extended JSON (v2)

### edit/div/{ticker}

Frontend для дополнения данных по дивидендам

### edit/port/tickers

Frontend для изменения перечня бумаг в портфеле, для которых необходимо отслеживать появление новых дивидендов

## Event streams

Основные потоки событий между правилами обработки событий изображены на схеме. 
Дополнительно каждое правило в случае возникновения ошибки направляет событие с ее описанием, 
которое обрабатывается специальным правилом записывающим сообщение в лог и Telegram.
```mermaid
flowchart
    Input[\Input/]-->Service:Raw{{Service:Raw}}
    Input[\Input/]-->Service:Port{{Service:Port}}
    Service:Raw-->Rule:Backup
    Service:Port-->Rule:Backup
    
    Timer[\Timer/]-->Rule:End
    Rule:End-->Rule:Dates
    
    Rule:Dates-->Rule:CPI
    Rule:Dates-->Rule:Indexes
    Rule:Dates-->Rule:USD
	Rule:Dates-->Rule:DivStatus

	Rule:USD-->Rule:Securities
    Rule:Securities-->Rule:Quotes
	Rule:Quotes-->Rule:Dividends
    
    Rule:DivStatus-->Rule:CheckRaw
    Rule:DivStatus-.->Rule:CheckReestry
    Rule:DivStatus-->Rule:CheckNASDAQ
```