import { writable } from "svelte/store";

interface Security {
	lot: number;
	price: number;
}

interface Account {
	cash: number;
	positions: Record<string, number>;
}

export interface Portfolio {
	day: string;
	accounts: Record<string, Account>;
	securities: Readonly<Record<string, Security>>;
}

export const portfolio = writable<Portfolio>({
	day: "",
	securities: {},
	accounts: {}
});
