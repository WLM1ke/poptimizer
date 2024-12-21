<script lang="ts">
	import { Card, CardMain, CardSecondary } from "$lib/components/card";
	import { portfolio } from "$lib/stores/portfolio";
	import { Table, TableHead, HeadCell, TableBody, TableRow, TextCell, PercentCell } from "$lib/components/table";
	import type { PageData } from "./$types";
	import { get } from "$lib/request";

	let { data }: { data: PageData } = $props();
	let forecast = $state(data);
	let optimization = $derived.by(() => {
		const maxLower = Math.max(...forecast.positions.map((pos) => pos.grad_lower));
		const minUpper = Math.min(...forecast.positions.map((pos) => (pos.weight > 0 ? pos.grad_upper : Infinity)));
		const breakEven = Math.min(maxLower, (maxLower + minUpper) / 2);

		const positions = forecast.positions.map((pos) => {
			return { ...pos, grad_lower: pos.grad_lower - breakEven, grad_upper: pos.grad_upper - breakEven };
		});

		const buy = positions.filter((pos) => pos.grad_lower >= 0);
		buy.sort((pos1, pos2) =>
			pos1.weight !== pos2.weight ? pos1.weight - pos2.weight : pos2.grad_lower - pos1.grad_lower
		);

		const sell = positions.filter((pos) => pos.grad_upper < 0 && pos.weight > 0);
		sell.sort((pos1, pos2) => pos2.weight * pos2.grad_upper - pos1.weight * pos1.grad_upper);

		return {
			breakEven,
			buy,
			sell
		};
	});

	$effect(() => {
		if ($portfolio.ver != forecast.portfolio_ver) {
			setTimeout(async () => {
				forecast = await get(fetch, `/api/forecast`);
			}, 1000);
		}
	});

	const percent = (num: number) => {
		return num.toLocaleString("RU", {
			style: "percent",
			minimumFractionDigits: 1,
			maximumFractionDigits: 1
		});
	};
</script>

<Card>
	<CardSecondary>
		Date: {forecast.day}
	</CardSecondary>
	<CardMain>Buy: {optimization.buy.length} / Sell: {optimization.sell.length}</CardMain>
	<CardSecondary>
		Breakeven: {percent(optimization.breakEven)} / Count: {forecast.forecasts_count}
	</CardSecondary>
</Card>
<Table>
	<TableHead>
		<HeadCell>Ticker</HeadCell>
		<HeadCell>Weight</HeadCell>
		<HeadCell>Lower bound</HeadCell>
		<HeadCell>Upper bound</HeadCell>
		<HeadCell>Signal</HeadCell>
	</TableHead>
	<TableBody>
		{#each optimization.buy as position (position.ticker)}
			<TableRow>
				<TextCell text={position.ticker} />
				<PercentCell value={position.weight} />
				<PercentCell value={position.grad_lower} />
				<PercentCell value={position.grad_upper} />
				<TextCell text="Buy" center />
			</TableRow>
		{/each}
		{#each optimization.sell as position (position.ticker)}
			<TableRow>
				<TextCell text={position.ticker} />
				<PercentCell value={position.weight} />
				<PercentCell value={position.grad_lower} />
				<PercentCell value={position.grad_upper} />
				<TextCell text="Sell" center />
			</TableRow>
		{/each}
	</TableBody>
</Table>
