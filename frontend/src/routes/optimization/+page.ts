import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";
import { get } from "$lib/request";

interface Positions {
	ticker: string;
	weight: number;
	grad_lower: number;
	grad_upper: number;
}

export interface Forecast {
	day: string;
	portfolio_ver: number;
	forecasts_count: number;
	risk_tolerance: number;
	positions: Positions[];
}

export const load: PageLoad = async ({ fetch }) => {
	const forecast: Forecast = await get(fetch, `/api/forecast`);
	if (forecast === undefined) {
		error(500, "Can't load forecast");
	}

	return forecast;
};
