import { error } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

interface DivCompareRow {
	day: Date;
	dividend: number;
	currency: "RUR" | "USD";
	status: "extra" | "ok" | "missed";
}

interface DivCompareRaw {
	day: string;
	dividend: number;
	currency: "RUR" | "USD";
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
		const dividends = await res.json();

		dividends.dividends = dividends.dividends.map(({ day, dividend, currency, status }: DivCompareRaw) => {
			return { day: new Date(`${day}Z`), dividend, currency, status };
		});

		return dividends as Dividends;
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
