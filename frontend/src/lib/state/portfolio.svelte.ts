import { del, get, post } from "$lib/request";
import { error, redirect } from "@sveltejs/kit";
import { accHideZeroPositions, accSortByValue, portSortByValue } from "./settings.svelte";
import { alerts } from "./alerts.svelte";

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
let redirected = false;

export const loadPortfolio = async (fetchFn: typeof fetch) => {
	const port: Portfolio | undefined = await get(fetchFn, "/api/portfolio");

	if (!port) {
		error(500, "Can't load portfolio");
	}

	portfolio = port;

	if (Object.keys(portfolio.account_names).length === 0 && !redirected) {
		alerts.addInfo("No accounts: create them in settings");
		redirected = true;
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

interface CompPosition {
	ticker: string;
	value: number;
}

const compTickers = (a: CompPosition, b: CompPosition) => {
	return a.ticker.localeCompare(b.ticker);
};
const compValue = (a: CompPosition, b: CompPosition) => {
	return b.value - a.value;
};

const sumValues = (account: Record<string, number>) => {
	return Object.values(account).reduce((acc, val) => acc + val, 0);
};

class PortfolioView {
	day = $derived(portfolio.day);
	ver = $derived(portfolio.ver);
	cash = $derived(sumValues(portfolio.cash));
	value = $derived(portfolio.positions.reduce((acc, pos) => acc + pos.price * sumValues(pos.accounts), this.cash));
	tickerAccounts = $derived(
		portfolio.positions.reduce((acc: Record<string, string>, { ticker, accounts }) => {
			acc[ticker] = Object.keys(accounts).sort().join(" ");
			return acc;
		}, {})
	);
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

export class AccountView {
	constructor(name: string) {
		this.name = name;
	}

	name = "";
	day = $derived(portfolio.day);
	cash = $derived(portfolio.cash[this.name] ?? 0);
	value = $derived(
		portfolio.positions.reduce((acc, pos) => acc + pos.price * (pos.accounts[this.name] ?? 0), this.cash)
	);
	positions = $derived(
		portfolio.positions
			.map((pos) => {
				const ticker = pos.ticker;
				const shares = pos.accounts[this.name] ?? 0;
				const lot = pos.lot;
				const price = pos.price;
				const value = price * shares;

				return {
					ticker,
					shares,
					lot,
					price,
					value
				};
			})
			.filter((pos) => pos.value !== 0 || !accHideZeroPositions.value)
			.sort(accSortByValue.value ? compValue : compTickers)
	);
	posCount = $derived(portfolio.positions.filter((pos) => pos.accounts[this.name] ?? 0 > 0).length);
	posTotal = $derived(portfolio.positions.length);

	updatePosition = async (ticker: string, amount: string) => {
		const port: Portfolio | undefined = await post(fetch, `/api/portfolio/${this.name}/${ticker}`, {
			amount
		});
		if (port !== undefined) {
			portfolio = port;
		}
	};
}
