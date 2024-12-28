import { del, get, post } from "$lib/request";
import { error, redirect } from "@sveltejs/kit";
import { alerts } from "./alerts.svelte";
import { portSortByValue } from "./settings.svelte";

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

let portfolio = $state<Portfolio>({ day: "", ver: -1, account_names: [], cash: {}, positions: [] });

export const loadPortfolio = async (fetchFn: typeof fetch) => {
	const port: Portfolio | undefined = await get(fetchFn, "/api/portfolio");

	if (!port) {
		error(500, "Can't load portfolio");
	}

	portfolio = port;

	if (Object.keys(portfolio.account_names).length === 0) {
		alerts.addInfo("No accounts: create them in settings");
		redirect(307, "/settings");
	}
};

class Accounts {
	accounts = $derived(portfolio.account_names);
	remove = async (account: string) => {
		const port = await del(fetch, `/api/portfolio/${account}`);
		if (port !== undefined) {
			portfolio = port;
		}
	};

	create = async (account: string) => {
		account = account[0].toUpperCase() + account.substring(1);
		const port = await post(fetch, `/api/portfolio/${account}`);
		if (port !== undefined) {
			portfolio = port;
		}
	};
}

export const accounts = new Accounts();

export interface CompPosition {
	ticker: string;
	value: number;
}

export const compTickers = (a: CompPosition, b: CompPosition) => {
	return a.ticker.localeCompare(b.ticker);
};
export const compValue = (a: CompPosition, b: CompPosition) => {
	return b.value - a.value;
};

const sumValues = (account: Record<string, number>) => {
	return Object.values(account).reduce((acc, val) => acc + val, 0);
};

export class PortfolioView {
	day = $derived(portfolio.day);
	cash = $derived(sumValues(portfolio.cash));
	value = $derived(portfolio.positions.reduce((acc, pos) => acc + pos.price * sumValues(pos.accounts), this.cash));
	positions = $derived(
		portfolio.positions
			.map((position) => {
				const ticker = position.ticker;
				const shares = sumValues(position.accounts);
				const price = position.price;
				const value = position.price * shares;
				const weight = this.value > 0 ? value / this.value : 0;

				return {
					ticker,
					shares,
					price,
					value,
					weight
				};
			})
			.filter((pos) => pos.value !== 0)
			.sort(portSortByValue.value ? compValue : compTickers)
	);
	positionsCount = $derived(portfolio.positions.length);
	effectiveCount = $derived(
		Math.round(
			this.value - this.cash > 0
				? 1 / Object.values(this.positions).reduce((acc, { weight }) => acc + weight * weight, 0)
				: 0
		)
	);
}

export const portfolioView = new PortfolioView();
