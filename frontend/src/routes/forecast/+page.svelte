<script lang="ts">
	import { Card, CardMain, CardSecondary } from "$lib/components/card";
	import { portfolio } from "$lib/stores/portfolio";
	import {
		Table,
		TableHead,
		HeadCell,
		TableBody,
		TableRow,
		TextCell,
		NumberCell,
		PercentCell
	} from "$lib/components/table";

	export let data;

	$: outdated = $portfolio.ver == data.portfolio_ver ? "" : "outdated";
</script>

<Card>
	<CardSecondary>
		Date: {data.day}
		{outdated}
	</CardSecondary>
	<CardMain>
		Mean: {data.mean.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})} / Std: {data.std.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})}
	</CardMain>
	<CardSecondary>
		Risk tolerance: {data.risk_tolerance.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})} / Count: {data.forecasts_count}
	</CardSecondary>
</Card>
<Table>
	<TableHead>
		<HeadCell>Ticker</HeadCell>
		<HeadCell>Mean</HeadCell>
		<HeadCell>Std</HeadCell>
		<HeadCell>Beta</HeadCell>
		<HeadCell>Gradient</HeadCell>
	</TableHead>
	<TableBody>
		{#each data.positions as position (position.ticker)}
			<TableRow>
				<TextCell text={position.ticker} />
				<PercentCell value={position.mean} />
				<PercentCell value={position.std} />
				<NumberCell value={position.beta} fractionDigits={2} />
				<PercentCell value={position.grad} />
			</TableRow>
		{/each}
	</TableBody>
</Table>
