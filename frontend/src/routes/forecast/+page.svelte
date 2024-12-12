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
	import type { PageData } from "./$types";
	import { get } from "$lib/request";

	let { data }: { data: PageData } = $props();
	let forecast = $state(data);

	$effect(() => {
		if ($portfolio.ver != forecast.portfolio_ver) {
			setTimeout(async () => {
				forecast = await get(fetch, `/api/forecast`);
			}, 1000);
		}
	});
</script>

<Card>
	<CardSecondary>
		Date: {forecast.day}
	</CardSecondary>
	<CardMain>
		Mean: {forecast.mean.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})} / Std: {forecast.std.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})}
	</CardMain>
	<CardSecondary>
		Risk tolerance: {forecast.risk_tolerance.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		})} / Count: {forecast.forecasts_count}
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
		{#each forecast.positions as position (position.ticker)}
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
