import { derived } from "svelte/store";
import { portfolio } from "$lib/stores/portfolio";
import { del, post } from "$lib/request";

export const removeAccount = async (account: string) => {
	const port = await del(fetch, `/api/portfolio/${account}`);
	if (port !== undefined) {
		portfolio.set(port);
	}
};
export const createAccount = async (account: string) => {
	account = account[0].toUpperCase() + account.substring(1);
	const port = await post(fetch, `/api/portfolio/${account}`);
	if (port !== undefined) {
		portfolio.set(port);
	}
};

export const accounts = derived(portfolio, (portfolio) => {
	return portfolio.account_names.toSorted();
});
