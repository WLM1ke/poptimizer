import { derived } from "svelte/store";
import { persistent } from "./persistent";
import { addError } from "./errors";

export interface Security {
	lot: number;
	price: number;
	turnover: number;
}

export interface Account {
	cash: number;
	positions: Record<string, number>;
}

export interface Portfolio {
	accounts: Record<string, Account>;
	securities: Record<string, Security>;
}

const portfolio = persistent<Portfolio>("portfolio", {
	securities: {},
	accounts: {}
});

export const load = async () => {
	try {
		const res = await fetch("/api/portfolio");
		if (!res.ok) {
			throw new Error(await res.text());
		}
		portfolio.set(await res.json());
	} catch (err) {
		let msg: string;
		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		addError(msg);
	}
};

export const accounts = derived(portfolio, (portfolio) => {
	return Object.keys(portfolio.accounts).toSorted();
});
