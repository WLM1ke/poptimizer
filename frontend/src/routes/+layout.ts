import { dividends } from "$lib/state/dividends.svelte";
import { loadPortfolio } from "$lib/state/portfolio.svelte";
import type { LayoutLoad } from "./$types";

export const ssr = false;

export const load: LayoutLoad = async ({ fetch }) => {
	await Promise.all([loadPortfolio(fetch), dividends.load(fetch)]);
};
