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

const sumValues = (account: Record<string, number>) => {
	return Object.values(account).reduce((accumulator, val) => accumulator + val, 0)
}

const retryDelay = 1000;

class PortfolioView {
	private _day = $state<string>("");
	private ver = $state<number>(-1);
	private account_names = $state<string[]>([]);
	private _cash = $state<Record<string, number>>({});
	private _positions = $state<Positions[]>([]);

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
	public cash = $derived(sumValues(this._cash));
	public value = $derived(this._positions.reduce((acc, pos) =>  acc + pos.price * sumValues(pos.accounts), this.cash));
	public positions = $derived(
		this._positions
			.map((position) => {
				const ticker = position.ticker;
				const shares = sumValues(position.accounts);
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
			.sort(portfolioSortByValue.get() ? compValue : compTickers)
	);
	public positionsCount = $derived(this._positions.length);
	public effectiveCount = $derived(
		Math.round(
			this.value - this.cash > 0
				? 1 / Object.values(this.positions).reduce((acc, { weight }) => acc + weight * weight, 0)
				: 0
		)
	);
}

export const port = new PortfolioView();
