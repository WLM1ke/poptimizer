import type { LayoutLoad } from "./$types";

export const ssr = false;

export const load = (async () => {
	return {
		accounts: ["Sberbank", "Tinkoff"]
	};
}) satisfies LayoutLoad;
