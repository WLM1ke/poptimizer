<script lang="ts">
	import { portfolioView } from "$lib/stores/portfolioView";
	import { Card, CardMain, CardSecondary } from "$lib/components/base/card";
	import {
		Table,
		TableHead,
		HeadCell,
		TableBody,
		TableRow,
		TextCell,
		NumberCell,
		EmptyCell,
		PercentCell
	} from "$lib/components/base/table";
</script>

<Card>
	<CardSecondary>
		Date: {$portfolioView.day}
	</CardSecondary>
	<CardMain>
		Value: {$portfolioView.value.toLocaleString(undefined, {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		})} &#8381;
	</CardMain>
	<CardSecondary>
		Positions: {$portfolioView.positionsCount} / Effective: {$portfolioView.effectiveCount}
	</CardSecondary>
</Card>
<Table>
	<TableHead>
		<HeadCell>Ticker</HeadCell>
		<HeadCell>Amount</HeadCell>
		<HeadCell>Price</HeadCell>
		<HeadCell>Value</HeadCell>
		<HeadCell>Weight</HeadCell>
	</TableHead>
	<TableBody>
		<TableRow>
			<TextCell text="Cash" />
			<NumberCell value={$portfolioView.cash} />
			<EmptyCell />
			<EmptyCell />
			<PercentCell value={$portfolioView.value > 0 ? $portfolioView.cash / $portfolioView.value : 1} />
		</TableRow>
		{#each $portfolioView.positions as position (position.ticker)}
			<TableRow>
				<TextCell text={position.ticker} />
				<NumberCell value={position.shares} />
				<NumberCell value={position.price} />
				<NumberCell value={position.value} fractionDigits={0} />
				<PercentCell value={position.weight} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
