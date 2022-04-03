# Микросервис для загрузки данных

Прототип в разработке - не используется в основном коде

## Endpoints

### api/{group}/{ticker}

Получение данных в формате MongoDB Extended JSON (v2)

### edit/{ticker}

Frontend для дополнения данных по дивидендам

## Event streams
```mermaid
flowchart
    Timer[\Timer/]-->End
    End-->Dates
    
    Dates-->CPI
    Dates-->Indexes
    Dates-->USD
	Dates-->DivStatus

	USD-->Securities
    Securities-->Quotes
	Quotes-->Dividends
    
    Input[\Input/]-->DivRaw
    DivRaw-.->Dividends
    DivRaw-->Backup
    
    DivStatus-->DivRaw
    DivStatus-.->CloseReestry
    DivStatus-.->NASDAQ
```