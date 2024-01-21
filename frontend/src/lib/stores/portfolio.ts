import { derived, writable } from "svelte/store";
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
	timestamp: string;
	accounts: Record<string, Account>;
	securities: Readonly<Record<string, Security>>;
}

export const portfolio = writable<Portfolio>({
	timestamp: "",
	securities: {},
	accounts: {}
});

export const fetchPortfolio = async (
	url: string,
	method: "GET" | "POST" | "DELETE" = "GET",
	body: BodyInit | undefined = undefined
) => {
	try {
		const res = await fetch(url, { method, body });
		if (!res.ok) {
			throw new Error(await res.text());
		}
		const port: Portfolio = await res.json();
		port.timestamp = port.timestamp.slice(0, 10);

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

		return true;
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

		return false;
	}
};

export const load = async () => {
	return await fetchPortfolio("/api/portfolio");
};
export const removeAccount = async (account: string) => {
	return await fetchPortfolio(`/api/portfolio/${account}`, "DELETE");
};
export const createAccount = async (account: string) => {
	account = account[0].toUpperCase() + account.substring(1);
	return await fetchPortfolio(`/api/portfolio/${account}`, "POST");
};

export const accounts = derived(portfolio, (portfolio) => {
	return Object.keys(portfolio.accounts).toSorted();
});
