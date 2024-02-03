import { writable } from "svelte/store";

export interface Tickers {
	tickers: string[];
}

export const tickers = writable<Tickers>({
	tickers: []
});
