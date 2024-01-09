import { writable } from "svelte/store";
import { type Portfolio } from "./types";

export const storable = <T>(key: string, initial: T) => {
	const saved = localStorage[key];
	if (!saved) {
		localStorage[key] = JSON.stringify(initial);
	}

	const { subscribe, set, update } = writable<T>(saved ? JSON.parse(saved) : initial);

	return {
		subscribe,
		set: (value: T) => {
			localStorage[key] = JSON.stringify(value);
			set(value);
		},
		update
	};
};

export const portfolio = storable<Portfolio>("portfolio", { securities: {}, accounts: {} });
