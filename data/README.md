# Микросервис для загрузки данных

Прототип в разработке - не используется в основном коде

## Потоки событий
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
	Securities-->Dividends
    
    Input[\Input/]-.->DivRaw
    DivRaw-.->Dividends
    
    DivStatus-->DivRaw
    DivStatus-.->CloseReestry
    DivStatus-.->NASDAQ
```