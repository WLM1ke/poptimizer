import { getDivTickers, getPortfolio } from "$lib/request";
import type { LayoutLoad } from "./$types";

export const ssr = false;

export const load = (async ({ fetch }) => {
	return {
		divTickers: await getDivTickers(fetch),
		portfolio: await getPortfolio(fetch)
	};
}) satisfies LayoutLoad;
