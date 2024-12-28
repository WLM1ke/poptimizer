import { get } from "$lib/request";
import { error, redirect } from "@sveltejs/kit";
import { alerts } from "./alerts.svelte";

interface Tickers {
	tickers: string[];
}

class Dividends {
	private _tickers = $state<string[]>([]);

	load = async (fetchFn: typeof fetch) => {
		const tickers: Tickers | undefined = await get(fetchFn, "/api/dividends");

		if (!tickers) {
			error(500, "Can't load dividend tickers");
		}

		for (const ticker of tickers.tickers) {
			alerts.addInfo(`Update dividends for ${ticker}`);
		}

		if (tickers.tickers.length > 0) {
			redirect(307, `/dividends/${tickers.tickers[0]}`);
		}
	};

	get tickers() {
		return this._tickers;
	}
}

export const dividends = new Dividends();
