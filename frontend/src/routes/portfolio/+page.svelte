<svelte:options runes />

<script lang="ts">
	import Card from "$lib/components/Card.svelte";
	import { Table, TableRow, TextCell, NumberCell, EmptyCell, PercentCell } from "$lib/components/table";
	import { formatNumber } from "$lib/format";
	import { port } from "$lib/state/portfolio.svelte";
</script>

<Card
	upper={`Date: ${port.day}`}
	main={`Value: ${formatNumber(port.value)} ₽`}
	lower={`Positions: ${port.positionsCount} / Effective: ${port.effectiveCount}`}
/>
<Table headers={["Ticker", "Amount", "Price", "Value", "Weight"]}>
	{#snippet rows()}
		<TableRow>
			{#snippet cells()}
				<TextCell text="Cash" />
				<NumberCell value={port.cash} />
				<EmptyCell />
				<EmptyCell />
				<PercentCell value={port.value > 0 ? port.cash / port.value : 1} />
			{/snippet}
		</TableRow>
		{#each port.positions as position (position.ticker)}
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
