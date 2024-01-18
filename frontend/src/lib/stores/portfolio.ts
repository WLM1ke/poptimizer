import { derived, writable } from "svelte/store";
import { addAlert } from "./alerts";
import { pageTitle } from "$lib/stores/page";

interface Security {
	lot: number;
	price: number;
	turnover: number;
}

interface Account {
	cash: number;
	positions: Record<string, number>;
}

interface Portfolio {
	accounts: Record<string, Account>;
	securities: Readonly<Record<string, Security>>;
}

const portfolio = writable<Portfolio>({
	securities: {},
	accounts: {}
});

const fetchPortfolio = async (url: string, method: "GET" | "POST" | "DELETE" = "GET") => {
	try {
		const res = await fetch(url, { method: method });
		if (!res.ok) {
			throw new Error(await res.text());
		}
		const port: Portfolio = await res.json();

		if (Object.keys(port.accounts).length === 0) {
			addAlert({
				info: true,
				msg: "No accounts: create them in settings"
			});
		}

		for (const [name, account] of Object.entries(port.accounts)) {
			if (Object.keys(account.positions).length === 0 && account.cash === 0) {
				addAlert({
					info: true,
					msg: `Account ${name} is empty: delete it or enter cash and positions`
				});
			}
		}

		portfolio.set(port);
	} catch (err) {
		let msg: string;
		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		addAlert({
			info: false,
			msg: msg
		});
	}
};

export const load = async () => {
	await fetchPortfolio("/api/portfolio");
};
export const removeAccount = async (account: string) => {
	await fetchPortfolio(`/api/portfolio/${account}`, "DELETE");
};
export const createAccount = async (account: string) => {
	account = account[0].toUpperCase() + account.substring(1);
	await fetchPortfolio(`/api/portfolio/${account}`, "POST");
};

export const accounts = derived(portfolio, (portfolio) => {
	return Object.keys(portfolio.accounts).toSorted();
});

export interface PortfolioPosition {
	ticker: string;
	shares: number;
	price: number;
	value: number;
	weight: number;
}

export const portfolioView = derived(portfolio, (port) => {
	let portfolioValue = 0;
	let portfolioCash = 0;
	const accountsPositions: Record<string, number> = {};

	for (const account of Object.values(port.accounts)) {
		portfolioValue += account.cash;
		portfolioCash += account.cash;
		for (const [ticker, shares] of Object.entries(account.positions)) {
			accountsPositions[ticker] = (accountsPositions[ticker] ?? 0) + shares;
			portfolioValue += shares * port.securities[ticker].price;
		}
	}

	const portfolioPositions = Object.entries(port.securities).map(([ticker, { price }]) => {
		const shares = accountsPositions[ticker] ?? 0;
		const value = price * shares;
		const weight = value / portfolioValue || 0;

		return {
			ticker,
			shares,
			price,
			value,
			weight
		};
	});

	return {
		positions: portfolioPositions,
		cash: portfolioCash,
		value: portfolioValue
	};
});

export interface AccountPosition {
	ticker: string;
	shares: number;
	lot: number;
	price: number;
	value: number;
}

export const accountView = derived([portfolio, pageTitle], ([port, accountName]) => {
	const account = port.accounts[accountName];
	if (account === undefined) {
		return {
			positions: [],
			cash: 0,
			value: 0
		};
	}

	const accountCash = account.cash;
	let accountValue = accountCash;

	const accountPositions = Object.entries(port.securities).map(([ticker, { price, lot }]) => {
		const shares = account.positions[ticker] ?? 0;
		const value = price * shares;
		accountValue += value;

		return {
			ticker,
			shares,
			lot,
			price,
			value
		};
	});

	return {
		positions: accountPositions,
		cash: accountCash,
		value: accountValue
	};
});
