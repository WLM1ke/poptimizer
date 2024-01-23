<script lang="ts">
	import { portfolioView } from "$lib/stores/portfolioView";
	import { Card, CardMain, CardSecondary } from "$lib/components/base/card";
	import {
		Table,
		TableHead,
		TableHeadCell,
		TableBody,
		TableRow,
		TableTickerCell,
		TableNumberCell,
		TableEmptyCell,
		TablePercentCell
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
		<TableHeadCell>Ticker</TableHeadCell>
		<TableHeadCell>Amount</TableHeadCell>
		<TableHeadCell>Price</TableHeadCell>
		<TableHeadCell>Value</TableHeadCell>
		<TableHeadCell>Weight</TableHeadCell>
	</TableHead>
	<TableBody>
		<TableRow>
			<TableTickerCell ticker="Cash" />
			<TableNumberCell value={$portfolioView.cash} />
			<TableEmptyCell />
			<TableEmptyCell />
			<TablePercentCell value={$portfolioView.value > 0 ? $portfolioView.cash / $portfolioView.value : 1} />
		</TableRow>
		{#each $portfolioView.positions as position (position.ticker)}
			<TableRow>
				<TableTickerCell ticker={position.ticker} />
				<TableNumberCell value={position.shares} />
				<TableNumberCell value={position.price} />
				<TableNumberCell value={position.value} fractionDigits={0} />
				<TablePercentCell value={position.weight} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
