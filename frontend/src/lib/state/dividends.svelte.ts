import { get, retryDelay } from "$lib/request";

export interface Tickers {
	tickers: string[];
}

class DivTickers {
	private tickers = $state<string[]>([]);

	update = async (fetchFn: typeof fetch) => {
		const tickers: Tickers = await get(fetchFn, "/api/dividends");

		if (!tickers) {
			setTimeout(() => this.update(fetchFn), retryDelay);

			return;
		}

		this.tickers = tickers.tickers;
	};

	get = () => this.tickers;
}

export const divTickers = new DivTickers();
