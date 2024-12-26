import type { LayoutLoad } from "./$types";
import { divTickers } from "$lib/state/dividends.svelte";
import { port } from "$lib/state/portfolio.svelte";

export const ssr = false;

export const load = (async ({ fetch }) => {
	await Promise.all([port.update(fetch), divTickers.update(fetch)]);
}) satisfies LayoutLoad;
