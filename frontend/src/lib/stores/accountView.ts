import { derived } from "svelte/store";
import { portfolio, fetchPortfolioAPI } from "$lib/stores/portfolio";
import { pageTitle } from "$lib/stores/page";
import { accountsHideZeroPositions, accountsSortByValue } from "$lib/stores/settings";

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

export const accountView = derived(
	[portfolio, pageTitle, accountsHideZeroPositions, accountsSortByValue],
	([port, pageTitle, hideZero, sortByValue]) => {
		const account = port.accounts[pageTitle];
		if (account === undefined) {
			return {
				timestamp: "",
				positions: [],
				positionsCount: 0,
				cash: 0,
				value: 0,
				updatePosition: async () => {}
			};
		}

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
			timestamp: port.timestamp,
			positions: accountPositions,
			positionsCount: Object.keys(account.positions).length,
			cash: accountCash,
			value: accountValue,
			updatePosition: async (ticker: string, amount: string) => {
				const body = JSON.stringify({ amount: amount });
				return await fetchPortfolioAPI(`/api/portfolio/${pageTitle}/${ticker}`, "POST", body);
			}
		};
	}
);
