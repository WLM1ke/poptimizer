import { get, retryDelay } from "$lib/request";
import { alerts } from "./alerts.svelte";
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

export interface CompPosition {
	ticker: string;
	value: number;
}

export const compTickers = (a: CompPosition, b: CompPosition) => {
	return a.ticker.localeCompare(b.ticker);
};
export const compValue = (a: CompPosition, b: CompPosition) => {
	return b.value - a.value;
};

const sumValues = (account: Record<string, number>) => {
	return Object.values(account).reduce((acc, val) => acc + val, 0);
};

class PortfolioView {
	day = $state<string>("");
	private ver = $state<number>(-1);
	accounts = $state<string[]>([]);
	accCash = $state<Record<string, number>>({});
	accPositions = $state<Positions[]>([]);

	update = async (fetchFn: typeof fetch) => {
		const port: Portfolio | undefined = await get(fetchFn, "/api/portfolio");

		if (!port) {
			setTimeout(() => this.update(fetchFn), retryDelay);

			return;
		}

		if (Object.keys(port.account_names).length === 0) {
			alerts.addInfo("No accounts: create them in settings");
		}

		this.day = port.day;
		this.ver = port.ver;
		this.accounts = port.account_names;
		this.accCash = port.cash;
		this.accPositions = port.positions;
	};

	cash = $derived(sumValues(this.accCash));
	value = $derived(this.accPositions.reduce((acc, pos) => acc + pos.price * sumValues(pos.accounts), this.cash));
	positions = $derived(
		this.accPositions
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
	positionsCount = $derived(this.accPositions.length);
	effectiveCount = $derived(
		Math.round(
			this.value - this.cash > 0
				? 1 / Object.values(this.positions).reduce((acc, { weight }) => acc + weight * weight, 0)
				: 0
		)
	);
}

export const port = new PortfolioView();
