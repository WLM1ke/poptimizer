import { derived } from "svelte/store";
import { portfolio } from "$lib/stores/portfolio";
import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/stores/settings";

export interface PortfolioPosition {
	ticker: string;
	shares: number;
	price: number;
	value: number;
	weight: number;
}

const compTickers = (a: PortfolioPosition, b: PortfolioPosition) => {
	return a.ticker.localeCompare(b.ticker);
};
const compValue = (a: PortfolioPosition, b: PortfolioPosition) => {
	return b.value - a.value;
};

export const portfolioView = derived(
	[portfolio, portfolioHideZeroPositions, portfolioSortByValue],
	([port, hideZero, sortByValue]) => {
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

		const portfolioPositions = Object.entries(port.securities)
			.map(([ticker, { price }]) => {
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
			})
			.filter((pos) => pos.value !== 0 || !hideZero)
			.sort(sortByValue ? compValue : compTickers);

		const effectiveCount = Math.round(
			1 / Object.values(portfolioPositions).reduce((acc, { weight }) => acc + (weight > 0 ? weight * weight : 0), 0) ||
				0
		);

		return {
			timestamp: port.timestamp,
			positions: portfolioPositions,
			positionsCount: Object.keys(accountsPositions).length,
			effectiveCount,
			cash: portfolioCash,
			value: portfolioValue
		};
	}
);
