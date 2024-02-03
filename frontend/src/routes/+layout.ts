import type { LayoutLoad } from "./$types";
import { type Portfolio, portfolio } from "$lib/stores/portfolio";
import { type Tickers, tickers } from "$lib/stores/dividends";
import { addInfo } from "$lib/components/alerts";
import { get } from "$lib/request";

export const ssr = false;

export const load = (async ({ fetch }) => {
	const data = {
		getTitle: (pathname: string) => {
			const path = decodeURI(pathname);
			if (path === "/") {
				return "Summary";
			}
			const lastSlash = path.lastIndexOf("/");

			return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
		}
	};
	const [div, port]: [Tickers, Portfolio] = await Promise.all([
		get(fetch, "/api/dividends"),
		get(fetch, "/api/portfolio")
	]);
	if (div === undefined || port === undefined) {
		return data;
	}

	portfolio.set(port);
	tickers.set(div);

	for (const ticker of div.tickers) {
		addInfo(`Update dividends for ${ticker}`);
	}

	if (Object.keys(port.accounts).length === 0) {
		addInfo("No accounts: create them in settings");
	}

	for (const [name, account] of Object.entries(port.accounts)) {
		if (Object.keys(account.positions).length === 0 && account.cash === 0) {
			addInfo(`Account ${name} is empty: delete it or enter cash and positions`);
		}
	}

	return data;
}) satisfies LayoutLoad;
