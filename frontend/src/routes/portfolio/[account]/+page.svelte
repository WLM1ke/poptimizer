<script lang="ts">
	import { invalidateAll } from "$app/navigation";
	import { accountView, type AccountPosition } from "$lib/stores/portfolio";
	import { accountsHideZeroPositions, accountsSortByValue } from "$lib/stores/settings";

	let cash: number;

	const compTickers = (a: AccountPosition, b: AccountPosition) => {
		return a.ticker.localeCompare(b.ticker);
	};
	const compValue = (a: AccountPosition, b: AccountPosition) => {
		return b.value - a.value;
	};
	const preparePositions = (positions: AccountPosition[]) => {
		const filtered = positions.filter((pos) => pos.value !== 0 || !$accountsHideZeroPositions);
		filtered.sort($accountsSortByValue ? compValue : compTickers);
		cash = $accountView.cash;

		return filtered;
	};

	interface FormEvent {
		target: EventTarget | null;
	}
	const onChange = async (event: FormEvent, ticker: string) => {
		const target = event.target as HTMLInputElement;
		if (!(await $accountView.updatePosition(ticker, target.value))) {
			await invalidateAll();
		}
	};
</script>

<div>
	Value: {$accountView.value.toLocaleString(undefined, {
		minimumFractionDigits: 0,
		maximumFractionDigits: 0
	})}
</div>
<div>
	Cash: <input
		bind:value={cash}
		on:change={(event) => {
			onChange(event, "CASH");
		}}
		class="rounded-md border border-bg-accent bg-bg-main p-1"
		type="text"
		placeholder="Enter account title"
	/>
</div>
<table>
	<thead>
		<th>Ticker</th>
		<th>Shares</th>
		<th>Lot</th>
		<th>Price</th>
		<th>Value</th>
	</thead>
	{#each preparePositions($accountView.positions) as position (position.ticker)}
		<tbody>
			<td>{position.ticker}</td>
			<td
				><input
					bind:value={position.shares}
					on:change={(event) => {
						onChange(event, position.ticker);
					}}
					class="rounded-md border border-bg-accent bg-bg-main p-1"
					type="text"
					placeholder="Enter account title"
				/></td
			>
			<td>{position.lot.toLocaleString()}</td>
			<td>{position.price.toLocaleString()}</td>
			<td
				>{position.value.toLocaleString(undefined, {
					minimumFractionDigits: 0,
					maximumFractionDigits: 0
				})}</td
			>
		</tbody>
	{/each}
</table>
