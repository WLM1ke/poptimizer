import { derived } from "svelte/store";
import { portfolio, type Portfolio } from "$lib/stores/portfolio";
import { post } from "$lib/request";
import { accountsHideZeroPositions, accountsSortByValue } from "$lib/state/settings.svelte";

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
	const accountCash = port.cash[accountName] ?? 0;
	let accountValue = accountCash;
	let positionsCount = 0;

	const accountPositions = port.positions
		.map((position) => {
			const ticker = position.ticker;
			const shares = position.accounts[accountName] ?? 0;
			const lot = position.lot;
			const price = position.price;
			const value = price * shares;
			accountValue += value;

			if (value > 0) {
				positionsCount++;
			}

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
		positionsCount: positionsCount,
		positionsTotal: port.positions.length,
		cash: accountCash,
		value: accountValue,
		updatePosition: async (ticker: string, amount: string) => {
			const portfolioData: Portfolio = await post(fetch, `/api/portfolio/${accountName}/${ticker}`, { amount });
			if (portfolioData !== undefined) {
				portfolio.set(portfolioData);
			}
		}
	};
};

export const accountViewFn = derived([portfolio], ([port]) => {
	return (accountName: string) => {
		return getAccountView(accountName, port, accountsHideZeroPositions.get(), accountsSortByValue.get());
	};
});
