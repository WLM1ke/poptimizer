import { compTickers, compValue, portfolio } from "./portfolio.svelte";
import { accHideZeroPositions, accSortByValue } from "./settings.svelte";

class AccountView {
	name = "";
	day = $derived(portfolio.day);
	cash = $derived(portfolio.accCash[this.name]);
	positions = $derived(
		portfolio.accPositions
			.map((pos) => {
				const ticker = pos.ticker;
				const shares = pos.accounts[this.name] ?? 0;
				const lot = pos.lot;
				const price = pos.price;
				const value = price * shares;

				return {
					ticker,
					shares,
					lot,
					price,
					value
				};
			})
			.filter((pos) => pos.value !== 0 || !accHideZeroPositions.get())
			.sort(accSortByValue.get() ? compValue : compTickers)
	);
	posCount = $derived(portfolio.accPositions.filter((pos) => pos.accounts[this.name] ?? 0 > 0).length);
	posTotal = $derived(portfolio.accPositions.length);
	value = $derived(
		portfolio.accPositions.reduce((acc, pos) => acc + pos.price * (pos.accounts[this.name] ?? 0), this.cash)
	);

	constructor(name: string) {
		this.name = name;
	}
}
