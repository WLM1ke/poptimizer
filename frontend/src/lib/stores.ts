import { writable } from "svelte/store";
import { page } from "$app/stores";
import { derived } from "svelte/store";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

export const storable = <T extends JsonValue>(key: string, initial: T) => {
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

export const pageTitle = derived(page, (page) => {
	const path = page.url.pathname;
	const lastSlash = path.lastIndexOf("/");
	return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
});
