<script lang="ts">
	import { Table, TableRow, TextCell, NumberCell, PercentCell } from "$lib/components/table";
	import type { PageData } from "./$types";
	import Card from "$lib/components/Card.svelte";
	import { formatPercent } from "$lib/format";
	import { invalidate } from "$app/navigation";
	import { portfolioView } from "$lib/state/portfolio.svelte";

	let { data }: { data: PageData } = $props();
	let forecast = $derived(data);
	let status = $derived(forecast.portfolio_ver != portfolioView.ver ? "outdate" : "");

	$effect(() => {
		if (forecast.portfolio_ver != portfolioView.ver) {
			setTimeout(async () => {
				invalidate(`/api/forecast`);
			}, 1000);
		}
	});
</script>

<Card
	upper={`Date: ${forecast.day} ${status}`}
	main={`Mean: ${formatPercent(forecast.mean)} / Std: ${formatPercent(forecast.std)}`}
	lower={`Risk tolerance: ${formatPercent(forecast.risk_tolerance)} / Count: ${forecast.forecasts_count}`}
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
