import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { get } from "$lib/request";

interface Positions {
	ticker: string;
	mean: number;
	std: number;
	beta: number;
	grad: number;
}

export interface Forecast {
	day: string;
	portfolio_ver: number;
	forecasts_count: number;
	risk_tolerance: number;
	mean: number;
	std: number;
	positions: Positions[];
}

export const load = (async ({ fetch }) => {
	const forecast: Forecast = await get(fetch, `/api/forecast`);
	if (forecast === undefined) {
		error(500, "Can't load forecast");
	}

	return forecast;
}) satisfies PageLoad;
