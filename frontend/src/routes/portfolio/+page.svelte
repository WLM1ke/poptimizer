<script lang="ts">
	import { portfolioView, type PortfolioPosition } from "$lib/stores/portfolio";
	import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/stores/settings";
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
	<CardSecondary>
		Date: {$portfolioView.timestamp}
	</CardSecondary>
	<CardMain>
		Value: {value.toLocaleString(undefined, {
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
			<TableNumberCell value={cash} />
			<TableEmptyCell />
			<TableEmptyCell />
			<TablePercentCell value={cash / value} />
		</TableRow>
		{#each positions as position (position.ticker)}
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
