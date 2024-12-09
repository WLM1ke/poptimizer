import { derived } from "svelte/store";
import { portfolio } from "$lib/stores/portfolio";
import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/stores/settings";

export interface PortfolioPosition {
	ticker: string;
	value: number;
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
		const portfolioCash = Object.values(port.cash).reduce((accumulator, cash) => accumulator + cash, 0);
		const positionsShares = port.positions.map((position) =>
			Object.values(position.accounts).reduce((accumulator, shares) => accumulator + shares, 0)
		);
		const portfolioValue = positionsShares.reduce(
			(accumulator, shares, n) => accumulator + shares * port.positions[n].price,
			portfolioCash
		);

		const portfolioPositions = positionsShares
			.map((shares, n) => {
				const position = port.positions[n];

				const ticker = position.ticker;
				const price = position.price;
				const value = position.price * shares;
				const weight = portfolioValue > 0 ? value / portfolioValue : 0;

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
			portfolioValue > 0
				? 1 / Object.values(portfolioPositions).reduce((acc, { weight }) => acc + (weight > 0 ? weight * weight : 0), 0)
				: 0
		);

		return {
			day: port.day,
			positions: portfolioPositions,
			positionsCount: port.positions.length,
			effectiveCount,
			cash: portfolioCash,
			value: portfolioValue
		};
	}
);
