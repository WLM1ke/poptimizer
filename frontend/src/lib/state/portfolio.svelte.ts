import { del, get, post } from "$lib/request";
import { error, redirect } from "@sveltejs/kit";
import { alerts } from "./alerts.svelte";
import { portSortByValue } from "./settings.svelte";

interface Positions {
	ticker: string;
	lot: number;
	price: number;
	accounts: Record<string, number>;
}

interface PortfolioDTO {
	day: string;
	ver: number;
	account_names: string[];
	cash: Record<string, number>;
	positions: Positions[];
}

class Portfolio {
	private port = $state<PortfolioDTO>({ day: "", ver: -1, account_names: [], cash: {}, positions: [] });

	load = async (fetchFn: typeof fetch) => {
		const port: PortfolioDTO | undefined = await get(fetchFn, "/api/portfolio");

		if (!port) {
			error(500, "Can't load portfolio");
		}

		this.port = port;

		if (Object.keys(this.port.account_names).length === 0) {
			alerts.addInfo("No accounts: create them in settings");
			redirect(307, "/settings");
		}
	};

	removeAccount = async (account: string) => {
		const port = await del(fetch, `/api/portfolio/${account}`);
		if (port !== undefined) {
			this.port = port;
		}
	};

	createAccount = async (account: string) => {
		account = account[0].toUpperCase() + account.substring(1);
		const port = await post(fetch, `/api/portfolio/${account}`);
		if (port !== undefined) {
			this.port = port;
		}
	};

	get accounts() {
		return this.port.account_names;
	}
}

export const portfolio = new Portfolio();

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

export class PortfolioView {
	private port = $state<PortfolioDTO>();

	cash = $derived(sumValues(this.port!.cash));
	value = $derived(this.port!.positions.reduce((acc, pos) => acc + pos.price * sumValues(pos.accounts), this.cash));
	positions = $derived(
		this.port!.positions.map((position) => {
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
			.sort(portSortByValue.get() ? compValue : compTickers)
	);
	positionsCount = $derived(this.port!.positions.length);
	effectiveCount = $derived(
		Math.round(
			this.value - this.cash > 0
				? 1 / Object.values(this.positions).reduce((acc, { weight }) => acc + weight * weight, 0)
				: 0
		)
	);
}
