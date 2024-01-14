import type { LayoutLoad } from "./$types";
import { load as loadPortfolio } from "$lib/stores/portfolio";

export const ssr = false;

export const load = (async () => {
	await loadPortfolio();
}) satisfies LayoutLoad;
