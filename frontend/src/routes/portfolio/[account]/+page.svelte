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
	Date: {$accountView.timestamp}
</div>
<div>
	Value: {$accountView.value.toLocaleString(undefined, {
		minimumFractionDigits: 0,
		maximumFractionDigits: 0
	})}
</div>
<table>
	<thead>
		<tr>
			<th>Ticker</th>
			<th>Shares</th>
			<th>Lot</th>
			<th>Price</th>
			<th>Value</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Cash</td>
			<td>
				<input
					bind:value={cash}
					on:change={(event) => {
						onChange(event, "CASH");
					}}
					class="border-bg-accent bg-bg-main rounded-md border p-1"
					type="text"
					placeholder="Enter account title"
				/>
			</td>
			<td></td>
			<td></td>
			<td>{cash}</td>
		</tr>
		{#each preparePositions($accountView.positions) as position (position.ticker)}
			<tr>
				<td>{position.ticker}</td>
				<td>
					<input
						bind:value={position.shares}
						on:change={(event) => {
							onChange(event, position.ticker);
						}}
						class="border-bg-accent bg-bg-main rounded-md border p-1"
						type="text"
						placeholder="Enter account title"
					/>
				</td>
				<td>{position.lot.toLocaleString()}</td>
				<td>{position.price.toLocaleString()}</td>
				<td>
					{position.value.toLocaleString(undefined, {
						minimumFractionDigits: 0,
						maximumFractionDigits: 0
					})}
				</td>
			</tr>
		{/each}
	</tbody>
</table>
