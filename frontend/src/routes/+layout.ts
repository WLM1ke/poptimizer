import { dividends } from "$lib/state/dividends.svelte";
import { portfolio } from "$lib/state/portfolio.svelte";
import type { LayoutLoad } from "./$types";

export const ssr = false;

export const load = (async ({ fetch }) => {
	await Promise.all([portfolio.load(fetch), dividends.load(fetch)]);

	return {};
}) satisfies LayoutLoad;
