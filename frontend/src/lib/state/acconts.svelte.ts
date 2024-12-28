import { compTickers, compValue, accounts } from "./portfolio.svelte";
import { accHideZeroPositions, accSortByValue } from "./settings.svelte";

class AccountView {
	name = "";
	day = $derived(accounts.day);
	cash = $derived(accounts.accCash[this.name]);
	positions = $derived(
		accounts.accPositions
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
	posCount = $derived(accounts.accPositions.filter((pos) => pos.accounts[this.name] ?? 0 > 0).length);
	posTotal = $derived(accounts.accPositions.length);
	value = $derived(
		accounts.accPositions.reduce((acc, pos) => acc + pos.price * (pos.accounts[this.name] ?? 0), this.cash)
	);

	constructor(name: string) {
		this.name = name;
	}
}
