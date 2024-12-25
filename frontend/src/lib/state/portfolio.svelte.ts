import { get } from "$lib/request";
import { portfolioSortByValue } from "./settings.svelte";

interface Positions {
	ticker: string;
	lot: number;
	price: number;
	accounts: Record<string, number>;
}

interface Portfolio {
	day: string;
	ver: number;
	account_names: string[];
	cash: Record<string, number>;
	positions: Positions[];
}

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

const retryDelay = 1000;

class PortfolioView {
	_day = $state<string>("");
	ver = $state<number>(-1);
	account_names = $state<string[]>([]);
	_cash = $state<Record<string, number>>({});
	_positions = $state<Positions[]>([]);

	update = async (fetchFn: typeof fetch) => {
		const port: Portfolio | undefined = await get(fetchFn, "/api/dividends");

		if (!port) {
			setTimeout(() => this.update(fetchFn), retryDelay);

			return;
		}

		this._day = port.day;
		this.ver = port.ver;
		this.account_names = port.account_names;
		this._cash = port.cash;
		this._positions = port.positions;
	};

	public day = $derived(this._day);
	public cash = $derived(Object.values(this._cash).reduce((accumulator, cash) => accumulator + cash, 0));
	public value = $derived(
		this._positions.reduce((acc, pos) => {
			const shares = Object.values(pos.accounts).reduce((acc, shares) => acc + shares, 0);
			return acc + pos.price * shares;
		}, this.cash)
	);
	public positions = $derived.by(() => {
		return this._positions
			.map((position) => {
				const ticker = position.ticker;
				const shares = Object.values(position.accounts).reduce((acc, shares) => acc + shares, 0);
				const price = position.price;
				const value = position.price * shares;
				const weight = this.value > 0 ? value / this.value : 0;

				return {
					ticker,
					shares,
					price,
					value,
					weight
				};
			})
			.filter((pos) => pos.value !== 0)
			.sort(portfolioSortByValue.get() ? compValue : compTickers);
	});
	public positionsCount = $derived(this._positions.length);
	public effectiveCount = $derived(
		Math.round(
			this.value > 0
				? 1 / Object.values(this.positions).reduce((acc, { weight }) => acc + (weight > 0 ? weight * weight : 0), 0)
				: 0
		)
	);
}

export const port = new PortfolioView();
