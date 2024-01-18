<script lang="ts">
	import { portfolioView, type PortfolioPosition } from "$lib/stores/portfolio";
	import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/stores/settings";

	$: positions = preparePositions($portfolioView.positions);
	$: cash = $portfolioView.cash;
	$: value = $portfolioView.value;

	const compTickers = (a: PortfolioPosition, b: PortfolioPosition) => {
		return a.ticker.localeCompare(b.ticker);
	};
	const compValue = (a: PortfolioPosition, b: PortfolioPosition) => {
		return b.value - a.value;
	};
	const preparePositions = (positions: PortfolioPosition[]) => {
		const filtered = positions.filter((pos) => pos.value !== 0 || !$portfolioHideZeroPositions);
		filtered.sort($portfolioSortByValue ? compValue : compTickers);

		return filtered;
	};
</script>

<div>Value: {value}</div>
<div>Cash: {cash}</div>
<table>
	<thead>
		<th>Ticker</th>
		<th>Shares</th>
		<th>Price</th>
		<th>Value</th>
		<th>Weight</th>
	</thead>
	{#each positions as position (position.ticker)}
		<tbody>
			<td>{position.ticker}</td>
			<td>{position.shares.toLocaleString()}</td>
			<td>{position.price.toLocaleString()}</td>
			<td
				>{position.value.toLocaleString(undefined, {
					minimumFractionDigits: 0,
					maximumFractionDigits: 0
				})}</td
			>
			<td
				>{position.weight.toLocaleString(undefined, {
					style: "percent",
					minimumFractionDigits: 2,
					maximumFractionDigits: 2
				})}</td
			>
		</tbody>
	{/each}
</table>
