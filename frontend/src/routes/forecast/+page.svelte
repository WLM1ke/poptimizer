<script lang="ts">
	import { portfolio } from "$lib/stores/portfolio";
	import { Table, TableRow, TextCell, NumberCell, PercentCell } from "$lib/components/table";
	import type { PageData } from "./$types";
	import { get } from "$lib/request";
	import Card from "$lib/components/Card.svelte";

	let { data }: { data: PageData } = $props();
	let forecast = $state(data);
	let status = $derived($portfolio.ver != forecast.portfolio_ver ? "outdate" : "");

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

<Card
	upper={`Date: ${forecast.day} ${status}`}
	main={`Mean: ${percent(forecast.mean)} / Std: ${percent(forecast.std)}`}
	lower={`Risk tolerance: ${percent(forecast.risk_tolerance)} / Count: ${forecast.forecasts_count}`}
/>
<Table headers={["Ticker", "Mean", "Std", "Beta", "Gradient"]}>
	{#snippet rows()}
		{#each forecast.positions as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<PercentCell value={position.mean} />
					<PercentCell value={position.std} />
					<NumberCell value={position.beta} fractionDigits={2} />
					<PercentCell value={position.grad} />
				{/snippet}
			</TableRow>
		{/each}
	{/snippet}
</Table>
