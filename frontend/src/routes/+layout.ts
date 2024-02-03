import type { LayoutLoad } from "./$types";
import { load as loadPortfolio } from "$lib/stores/portfolio";
import { addInfo, addAlert } from "$lib/components/alerts";

export const ssr = false;

interface DivTickers {
	tickers: string[];
}
export const load = (async ({ fetch }) => {
	const loadDivTickers = async () => {
		try {
			const res = await fetch("/api/dividends");
			if (!res.ok) {
				throw new Error(await res.text());
			}
			const tickers: DivTickers = await res.json();

			for (const ticker of tickers.tickers) {
				addInfo(`Update dividends for ${ticker}`);
			}

			return tickers;
		} catch (err) {
			let msg: string;
			if (err instanceof Error) {
				msg = err.message;
			} else {
				msg = JSON.stringify(err);
			}
			addAlert(msg);
		}
	};

	const rez = await Promise.all([loadDivTickers(), loadPortfolio()]);

	return rez[0] ?? { tickers: [] };
}) satisfies LayoutLoad;
