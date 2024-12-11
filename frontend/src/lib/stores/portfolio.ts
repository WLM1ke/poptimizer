import { writable } from "svelte/store";

interface Positions {
	ticker: string;
	lot: number;
	price: number;
	accounts: Record<string, number>;
}

export interface Portfolio {
	day: string;
	ver: number;
	account_names: string[];
	cash: Record<string, number>;
	positions: Positions[];
}

export const portfolio = writable<Portfolio>({
	day: "",
	ver: 0,
	account_names: [],
	cash: {},
	positions: []
});
