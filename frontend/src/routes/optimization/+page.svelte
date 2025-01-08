<script lang="ts">
	import Card from "$lib/components/Card.svelte";
	import { Table, TableRow, TextCell, PercentCell } from "$lib/components/table";
	import type { PageData } from "./$types";
	import { formatPercent } from "$lib/format";
	import { portfolioView } from "$lib/state/portfolio.svelte";
	import { invalidate } from "$app/navigation";

	let { data }: { data: PageData } = $props();
	let forecast = $derived(data);
	let status = $derived(portfolioView.ver != forecast.portfolio_ver ? "outdate" : "");
	let optimization = $derived.by(() => {
		const maxLower = Math.max(...forecast.positions.map((pos) => pos.grad_lower));
		const minUpper = Math.min(...forecast.positions.map((pos) => (pos.weight > 0 ? pos.grad_upper : Infinity)));
		const breakEven = Math.min(maxLower, (maxLower + minUpper) / 2);

		const buy = forecast.positions
			.filter((pos) => pos.grad_lower >= breakEven)
			.map(({ weight, ticker, grad_lower, grad_upper }) => {
				return { weight, ticker, grad_lower, grad_upper, priority: grad_lower - breakEven };
			});
		buy.sort((pos1, pos2) => pos2.priority - pos1.priority);

		const sell = forecast.positions
			.filter((pos) => pos.grad_upper < breakEven && pos.weight > 0)
			.map(({ weight, ticker, grad_lower, grad_upper }) => {
				const accounts = portfolioView.tickerAccounts[ticker];

				return { weight, ticker, grad_lower, grad_upper, priority: grad_upper - breakEven, accounts };
			});
		sell.sort((pos1, pos2) => pos2.priority - pos1.priority);

		return {
			breakEven,
			buy,
			sell
		};
	});

	const firstRetry = 1000;
	const backOffFactor = 2;
	let retryDelay = firstRetry;

	$effect(() => {
		if (forecast.portfolio_ver != portfolioView.ver) {
			setTimeout(async () => {
				invalidate(`/api/forecast`);
			}, retryDelay);
			retryDelay *= backOffFactor;

			return;
		}

		retryDelay = firstRetry;
	});
</script>

<Card
	upper={`Date: ${forecast.day} ${status}`}
	main={`Buy tickets: ${optimization.buy.length} / Sell tickets : ${optimization.sell.length}`}
	lower={`Forecasts: ${forecast.forecasts_count} / Breakeven: ${formatPercent(optimization.breakEven)}`}
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
					<TextCell text={position.accounts} center />
				{/snippet}
			</TableRow>
		{/each}
	{/snippet}
</Table>
