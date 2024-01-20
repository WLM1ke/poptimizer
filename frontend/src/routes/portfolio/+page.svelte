<script lang="ts">
	import { portfolioView, type PortfolioPosition } from "$lib/stores/portfolio";
	import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/stores/settings";
	import Card from "$lib/components/base/Card.svelte";

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

<Card>
	<svelte:fragment slot="header">
		Date: {$portfolioView.timestamp}
	</svelte:fragment>
	<svelte:fragment slot="main">
		Value: {value.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})} &#8381;
	</svelte:fragment>
	<svelte:fragment slot="footer">
		Positions: {$portfolioView.positionsCount} / Effective: {$portfolioView.effectiveCount}
	</svelte:fragment>
</Card>
<table>
	<thead>
		<tr>
			<th>Ticker</th>
			<th>Amount</th>
			<th>Price</th>
			<th>Value</th>
			<th>Weight</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Cash</td>
			<td>{cash}</td>
			<td></td>
			<td></td>
			<td
				>{(cash / value).toLocaleString(undefined, {
					style: "percent",
					minimumFractionDigits: 1,
					maximumFractionDigits: 1
				})}</td
			>
		</tr>
		{#each positions as position (position.ticker)}
			<tr>
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
						minimumFractionDigits: 1,
						maximumFractionDigits: 1
					})}</td
				>
			</tr>
		{/each}
	</tbody>
</table>
