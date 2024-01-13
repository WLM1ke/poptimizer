import { derived } from "svelte/store";
import { persistent } from "./persistent";
import { addAlert } from "./alerts";

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

const portfolio = persistent<Portfolio>("portfolio", {
	securities: {},
	accounts: {}
});

const fetchPortfolio = async (url: string, method: "GET" | "POST" | "DELETE" = "GET") => {
	try {
		const res = await fetch(url, { method: method });
		if (!res.ok) {
			throw new Error(await res.text());
		}
		const port = await res.json();
		if (Object.keys(port.accounts).length === 0) {
			addAlert({
				info: true,
				msg: "Create account in settings"
			});
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
	await fetchPortfolio(`/api/portfolio/${account}`, "POST");
};

export const accounts = derived(portfolio, (portfolio) => {
	return Object.keys(portfolio.accounts).toSorted();
});

export const securities = derived(portfolio, (portfolio) => {
	return portfolio.securities;
});
