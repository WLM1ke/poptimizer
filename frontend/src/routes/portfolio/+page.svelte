<script lang="ts">
	import { portfolioView } from "$lib/stores/portfolioView";
	import Card from "$lib/components/Card.svelte";
	import { Table, TableRow, TextCell, NumberCell, EmptyCell, PercentCell } from "$lib/components/table";
</script>

<Card
	upper={`Date: ${$portfolioView.day}`}
	main={`Value: ${$portfolioView.value.toLocaleString("RU", { minimumFractionDigits: 0, maximumFractionDigits: 0 })} &#8381;`}
	lower={`Positions: ${$portfolioView.positionsCount} / Effective: ${$portfolioView.effectiveCount}`}
/>
<Table headers={["Ticker", "Amount", "Price", "Value", "Weight"]}>
	{#snippet rows()}
		<TableRow>
			{#snippet cells()}
				<TextCell text="Cash" />
				<NumberCell value={$portfolioView.cash} />
				<EmptyCell />
				<EmptyCell />
				<PercentCell value={$portfolioView.value > 0 ? $portfolioView.cash / $portfolioView.value : 1} />
			{/snippet}
		</TableRow>
		{#each $portfolioView.positions as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<NumberCell value={position.shares} />
					<NumberCell value={position.price} />
					<NumberCell value={position.value} fractionDigits={0} />
					<PercentCell value={position.weight} />
				{/snippet}
			</TableRow>
		{/each}
	{/snippet}
</Table>
