import type { PageLoad } from "./$types";
import { Dividends } from "$lib/state/dividends.svelte";

export const load: PageLoad = async ({ fetch, params }) => {
	const dividends = new Dividends(params.ticker);

	await dividends.load(fetch);

	return { dividends };
};
