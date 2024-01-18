<script lang="ts">
	import { accountView, type AccountPosition } from "$lib/stores/portfolio";
	import { accountsHideZeroPositions, accountsSortByValue } from "$lib/stores/settings";

	$: positions = preparePositions($accountView.positions);
	$: cash = $accountView.cash;
	$: value = $accountView.value;

	const compTickers = (a: AccountPosition, b: AccountPosition) => {
		return a.ticker.localeCompare(b.ticker);
	};
	const compValue = (a: AccountPosition, b: AccountPosition) => {
		return b.value - a.value;
	};
	const preparePositions = (positions: AccountPosition[]) => {
		const filtered = positions.filter((pos) => pos.value !== 0 || !$accountsHideZeroPositions);
		filtered.sort($accountsSortByValue ? compValue : compTickers);

		return filtered;
	};
</script>

<div>Value: {value}</div>
<div>Cash: {cash}</div>
<table>
	<thead>
		<th>Ticker</th>
		<th>Shares</th>
		<th>Lot</th>
		<th>Price</th>
		<th>Value</th>
	</thead>
	{#each positions as position (position.ticker)}
		<tbody>
			<td>{position.ticker}</td>
			<td>{position.shares.toLocaleString()}</td>
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
