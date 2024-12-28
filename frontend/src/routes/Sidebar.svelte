<svelte:options runes />

<script lang="ts">
	import LowerSidebar from "./LowerSidebar.svelte";
	import MenuItem from "./MenuItem.svelte";
	import PortfolioIcon from "$lib/icons/PortfolioIcon.svelte";
	import ForecastIcon from "$lib/icons/ForecastIcon.svelte";
	import OptimizationIcon from "$lib/icons/OptimizationIcon.svelte";
	import DividendsIcon from "$lib/icons/DividendsIcon.svelte";
	import AccountIcon from "$lib/icons/AccountIcon.svelte";
	import { scale } from "svelte/transition";
	import { flip } from "svelte/animate";
	import { accounts } from "$lib/state/portfolio.svelte";
	import { divTickers } from "$lib/state/dividends.svelte";
</script>

<aside class="border-bg-accent bg-bg-sidebar flex flex-col justify-between border-r p-2">
	<nav class="flex flex-col gap-2">
		<ul class="flex flex-col gap-1">
			<li>
				<MenuItem title="Portfolio" href="/portfolio">
					{#snippet icon()}
						<PortfolioIcon />
					{/snippet}
				</MenuItem>
			</li>
			<li>
				<ul class="flex flex-col gap-1">
					{#each accounts.accounts as account (account)}
						<li transition:scale animate:flip>
							<MenuItem title={account} href="/portfolio/{account}" subItem>
								{#snippet icon()}
									<AccountIcon />
								{/snippet}
							</MenuItem>
						</li>
					{/each}
				</ul>
			</li>
			<li>
				<MenuItem title="Forecast" href="/forecast">
					{#snippet icon()}
						<ForecastIcon />
					{/snippet}
				</MenuItem>
			</li>
			<li>
				<MenuItem title="Optimization" href="/optimization">
					{#snippet icon()}
						<OptimizationIcon />
					{/snippet}
				</MenuItem>
			</li>
		</ul>
		{#if divTickers.tickers.length > 0}
			<ul class="border-bg-medium flex flex-col gap-1 border-t pt-2" transition:scale>
				<li>
					<MenuItem title="Dividends">
						{#snippet icon()}
							<DividendsIcon />
						{/snippet}
					</MenuItem>
				</li>
				<li>
					<ul class="flex flex-col gap-1">
						{#each divTickers.tickers as ticker (ticker)}
							<li transition:scale animate:flip>
								<MenuItem title={ticker} href="/dividends/{ticker}" subItem>
									{#snippet icon()}
										<AccountIcon />
									{/snippet}
								</MenuItem>
							</li>
						{/each}
					</ul>
				</li>
			</ul>
		{/if}
	</nav>
	<LowerSidebar />
</aside>
