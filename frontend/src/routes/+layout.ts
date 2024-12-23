import type { LayoutLoad } from "./$types";
import { type Portfolio, portfolio } from "$lib/stores/portfolio";
import { type Tickers, tickers } from "$lib/stores/dividends";
import { get } from "$lib/request";
import { alerts } from "$lib/state/alerts.svelte";

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
		alerts.addInfo(`Update dividends for ${ticker}`);
	}

	if (Object.keys(port.account_names).length === 0) {
		alerts.addInfo("No accounts: create them in settings");
	}

	for (const name of port.account_names) {
		if (
			port.positions.reduce(
				(accumulator, position) => accumulator + (position.accounts[name] ?? 0),
				port.cash[name] ?? 0
			) === 0
		) {
			alerts.addInfo(`Account ${name} is empty: delete it or enter cash and positions`);
		}
	}

	return data;
}) satisfies LayoutLoad;
