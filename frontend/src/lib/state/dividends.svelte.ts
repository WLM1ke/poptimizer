import { get, put } from "$lib/request";
import { error, redirect } from "@sveltejs/kit";
import { alerts } from "./alerts.svelte";

interface Tickers {
	tickers: string[];
}

class DivTickers {
	private _tickers = $state<string[]>([]);
	redirected = false;

	load = async (fetchFn: typeof fetch) => {
		const tickers: Tickers | undefined = await get(fetchFn, "/api/dividends");

		if (!tickers) {
			error(500, "Can't load dividend tickers");
		}

		this._tickers = tickers.tickers;

		if (tickers.tickers.length > 0 && !this.redirected) {
			alerts.addInfo(`Update dividends`);
			this.redirected = true;
			redirect(307, `/dividends/${tickers.tickers[0]}`);
		}
	};

	get tickers() {
		return this._tickers;
	}
}

export const divTickers = new DivTickers();

interface DivRow {
	day: string;
	dividend: number;
	status: "extra" | "ok" | "missed";
}

interface DivDTO {
	dividends: DivRow[];
}

const fractionDigits = (num: number) => {
	const numString = num.toString();
	const pointPos = numString.indexOf(".");

	if (pointPos === -1) {
		return 0;
	}

	return numString.length - pointPos - 1;
};

export class Dividends {
	ticker = "";
	dividends = $state<DivRow[]>([]);
	next = $state({
		day: new Date().toISOString().slice(0, 10),
		dividend: 1
	});
	maxFractionDigits = $derived(
		Math.max(...this.dividends.map((currentValue) => fractionDigits(currentValue.dividend)))
	);

	constructor(ticker: string) {
		this.ticker = ticker;
	}
	load = async (fetchFn: typeof fetch) => {
		const div: DivDTO | undefined = await get(fetchFn, `/api/dividends/${this.ticker}`);
		if (div === undefined) {
			error(500, "Can't load dividends");
		}

		this.dividends = div.dividends;
		const lastRow = div.dividends[div.dividends.length - 1];
		this.next = {
			day: lastRow?.day ?? new Date().toISOString().slice(0, 10),
			dividend: lastRow?.dividend ?? 1
		};
	};
	toggleRow = (index: number) => {
		switch (this.dividends[index].status) {
			case "extra":
				this.dividends[index].status = "missed";
				break;
			case "missed":
				this.dividends[index].status = "extra";
		}
	};
	addRow = () => {
		if (typeof this.next.dividend !== "number") {
			alerts.addAlert("Dividend should be number");
			return;
		}
		const date = new Date(this.next.day);
		if (date.toString() === "Invalid Date") {
			alerts.addAlert("Invalid Date");
			return;
		}
		this.dividends.push({
			day: date.toISOString().slice(0, 10),
			dividend: this.next.dividend,
			status: "extra"
		});
	};
	update = async () => {
		const div: DivDTO | undefined = await put(fetch, `/api/dividends/${this.ticker}`, {
			dividends: this.dividends
				.filter(({ status }) => {
					return status === "ok" || status === "extra";
				})
				.map(({ day, dividend }) => {
					return { day, dividend };
				})
				.toSorted((a, b) => {
					return a.day !== b.day ? a.day.localeCompare(b.day) : a.dividend - b.dividend;
				})
		});

		if (div !== undefined) {
			this.dividends = div.dividends;
		}
	};
}
