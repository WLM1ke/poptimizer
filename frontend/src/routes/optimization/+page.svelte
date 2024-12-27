<!-- <script lang="ts">
	import Card from "$lib/components/Card.svelte";
	import { portfolio } from "$lib/stores/portfolio";
	import { Table, TableRow, TextCell, PercentCell } from "$lib/components/table";
	import type { PageData } from "./$types";
	import { get } from "$lib/request";
	import { formatPercent } from "$lib/format";

	let { data }: { data: PageData } = $props();
	let forecast = $state(data);
	let status = $derived($portfolio.ver != forecast.portfolio_ver ? "outdate" : "");
	let optimization = $derived.by(() => {
		const maxLower = Math.max(...forecast.positions.map((pos) => pos.grad_lower));
		const minUpper = Math.min(...forecast.positions.map((pos) => (pos.weight > 0 ? pos.grad_upper : Infinity)));
		const breakEven = Math.min(maxLower, (maxLower + minUpper) / 2);

		const buy = forecast.positions
			.filter((pos) => pos.grad_lower >= breakEven)
			.map(({ weight, ticker, grad_lower, grad_upper }) => {
				return { weight, ticker, grad_lower, grad_upper, priority: grad_lower - breakEven };
			});
		buy.sort((pos1, pos2) => (pos1.weight !== pos2.weight ? pos1.weight - pos2.weight : pos2.priority - pos1.priority));

		const sell = forecast.positions
			.filter((pos) => pos.grad_upper < breakEven && pos.weight > 0)
			.map(({ weight, ticker, grad_lower, grad_upper }) => {
				return { weight, ticker, grad_lower, grad_upper, priority: grad_upper - breakEven };
			});
		sell.sort((pos1, pos2) => pos2.weight * pos2.priority - pos1.weight * pos1.priority);

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
</script>

<Card
	upper={`Date: ${forecast.day} ${status}`}
	main={`Buy: ${optimization.buy.length} / Sell: ${optimization.sell.length}`}
	lower={`Breakeven: ${formatPercent(optimization.breakEven)} / Count: ${forecast.forecasts_count}`}
/>
<Table headers={["Ticker", "Weight", "Lower bound", "Upper bound", "Priority", "Signal"]}>
	{#snippet rows()}
		{#each optimization.buy as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<PercentCell value={position.weight} />
					<PercentCell value={position.grad_lower} />
					<PercentCell value={position.grad_upper} />
					<PercentCell value={position.priority} />
					<TextCell text="Buy" center />
				{/snippet}
			</TableRow>
		{/each}
		{#each optimization.sell as position (position.ticker)}
			<TableRow>
				{#snippet cells()}
					<TextCell text={position.ticker} />
					<PercentCell value={position.weight} />
					<PercentCell value={position.grad_lower} />
					<PercentCell value={position.grad_upper} />
					<PercentCell value={position.priority} />
					<TextCell text="Sell" center />
				{/snippet}
			</TableRow>
		{/each}
	{/snippet}
</Table> -->
