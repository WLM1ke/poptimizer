import { writable } from "svelte/store";
import { derived } from "svelte/store";
import { page } from "$app/stores";

export const errors = writable<Array<string>>([]);
export const pageTitle = derived(page, (page) => {
	const path = page.url.pathname;
	const lastSlash = path.lastIndexOf("/");
	return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
});
