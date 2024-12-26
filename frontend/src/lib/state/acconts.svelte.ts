import { compTickers, compValue, port } from "./portfolio.svelte";
import { accountsHideZeroPositions, accountsSortByValue } from "./settings.svelte";

class AccountView {
	name = "";
	day = $derived(port.day);
	cash = $derived(port.accCash[this.name]);
	positions = $derived(
		port.accPositions
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
			.filter((pos) => pos.value !== 0 || !accountsHideZeroPositions.get())
			.sort(accountsSortByValue.get() ? compValue : compTickers)
	);
	posCount = $derived(port.accPositions.filter((pos) => pos.accounts[this.name] ?? 0 > 0).length);
	posTotal = $derived(port.accPositions.length);
	value = $derived(port.accPositions.reduce((acc, pos) => acc + pos.price * (pos.accounts[this.name] ?? 0), this.cash));

	constructor(name: string) {
		this.name = name;
	}
}
