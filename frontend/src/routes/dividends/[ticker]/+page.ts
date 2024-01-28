import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

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
	try {
		const res = await fetch(`/api/dividends/${params.ticker}`);
		if (!res.ok) {
			throw new Error(await res.text());
		}

		return (await res.json()) as Dividends;
	} catch (err) {
		let msg: string;
		if (err instanceof Error) {
			msg = err.message;
		} else {
			msg = JSON.stringify(err);
		}
		error(500, msg);
	}
}) satisfies PageLoad;
