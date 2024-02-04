import { derived } from "svelte/store";
import { portfolio, type Portfolio } from "$lib/stores/portfolio";
import { accountsHideZeroPositions, accountsSortByValue } from "$lib/stores/settings";
import { post } from "$lib/request";
import { invalidate } from "$app/navigation";

export interface AccountPosition {
	ticker: string;
	value: number;
}

const compTickers = (a: AccountPosition, b: AccountPosition) => {
	return a.ticker.localeCompare(b.ticker);
};
const compValue = (a: AccountPosition, b: AccountPosition) => {
	return b.value - a.value;
};

const getAccountView = (accountName: string, port: Portfolio, hideZero: boolean, sortByValue: boolean) => {
	const account = port.accounts[accountName];
	const accountCash = account.cash;
	let accountValue = accountCash;

	const accountPositions = Object.entries(port.securities)
		.map(([ticker, { price, lot }]) => {
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
		})
		.filter((pos) => pos.value !== 0 || !hideZero)
		.sort(sortByValue ? compValue : compTickers);

	return {
		name: accountName,
		day: port.day,
		positions: accountPositions,
		positionsCount: Object.keys(account.positions).length,
		positionsTotal: Object.keys(port.securities).length,
		cash: accountCash,
		value: accountValue,
		updatePosition: async (ticker: string, amount: string) => {
			const portfolioData: Portfolio = await post(fetch, `/api/portfolio/${accountName}/${ticker}`, { amount });
			if (portfolioData === undefined) {
				invalidate("/api/portfolio");

				return;
			}

			portfolio.set(portfolioData);
		}
	};
};

export const accountViewFn = derived(
	[portfolio, accountsHideZeroPositions, accountsSortByValue],
	([port, hideZero, sortByValue]) => {
		return (accountName: string) => {
			return getAccountView(accountName, port, hideZero, sortByValue);
		};
	}
);
