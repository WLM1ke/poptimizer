import { invalidate } from "$app/navigation";
import { alerts } from "$lib/state/alerts.svelte";
import { error, redirect } from "@sveltejs/kit";

export const retryDelay = 1000;

const request = async (
	fetchFn: typeof fetch,
	url: string,
	method: "GET" | "POST" | "PUT" | "DELETE",
	body: object | undefined = undefined
) => {
	try {
		const res = await fetchFn(url, { method, body: JSON.stringify(body) });
		if (!res.ok) {
			throw new Error(await res.text());
		}
		if (res.status === 204) {
			return null;
		}

		return await res.json();
	} catch (err) {
		let msg: string;

		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		alerts.addAlert(`${msg}`);

		setTimeout(() => invalidate("/api/dividends"), retryDelay);

		return undefined;
	}
};

export const get = async (fetchFn: typeof fetch, url: string) => {
	return await request(fetchFn, url, "GET");
};

export const post = async (fetchFn: typeof fetch, url: string, body: object | undefined = undefined) => {
	return await request(fetchFn, url, "POST", body);
};

export const put = async (fetchFn: typeof fetch, url: string, body: object | undefined = undefined) => {
	return await request(fetchFn, url, "PUT", body);
};

export const del = async (fetchFn: typeof fetch, url: string) => {
	return await request(fetchFn, url, "DELETE");
};

interface Tickers {
	tickers: string[];
}

export const getDivTickers = async (fetchFn: typeof fetch) => {
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

	return tickers.tickers;
};

interface Positions {
	ticker: string;
	lot: number;
	price: number;
	accounts: Record<string, number>;
}

interface Portfolio {
	day: string;
	ver: number;
	account_names: string[];
	cash: Record<string, number>;
	positions: Positions[];
}

export const getPortfolio = async (fetchFn: typeof fetch) => {
	const port: Portfolio | undefined = await get(fetchFn, "/api/portfolio");

	if (!port) {
		error(500, "Can't load portfolio");
	}

	if (Object.keys(port.account_names).length === 0) {
		alerts.addInfo("No accounts: create them in settings");
		redirect(307, "/settings");
	}

	return port;
};
