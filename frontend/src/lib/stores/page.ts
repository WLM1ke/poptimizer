import { derived } from "svelte/store";
import { page } from "$app/stores";

export const pageTitle = derived(page, (page) => {
	const path = decodeURI(page.url.pathname);
	if (path === "/") {
		return "Summary";
	}

	const lastSlash = path.lastIndexOf("/");
	return path[lastSlash + 1].toUpperCase() + path.substring(lastSlash + 2);
});
