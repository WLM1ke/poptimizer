import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { get } from "$lib/request";

interface DivCompareRow {
	day: string;
	dividend: number;
	currency: "rur" | "usd";
	status: "extra" | "ok" | "missed";
}

interface Dividends {
	dividends: DivCompareRow[];
}

export const load = (async ({ fetch, params }) => {
	const div: Dividends = await get(fetch, `/api/dividends/${params.ticker}`);
	if (div === undefined) {
		error(500, "Can't load dividends");
	}

	return { ...div, ticker: params.ticker };
}) satisfies PageLoad;
