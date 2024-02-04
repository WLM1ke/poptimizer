<script lang="ts">
	import LowerSidebar from "./LowerSidebar.svelte";
	import MenuItem from "./MenuItem.svelte";
	import PortfolioIcon from "$lib/icons/PortfolioIcon.svelte";
	import ForecastIcon from "$lib/icons/ForecastIcon.svelte";
	import OptimizationIcon from "$lib/icons/OptimizationIcon.svelte";
	import DividendsIcon from "$lib/icons/DividendsIcon.svelte";
	import AccountIcon from "$lib/icons/AccountIcon.svelte";
	import { scale } from "svelte/transition";
	import { accounts } from "$lib/stores/settings";
	import { flip } from "svelte/animate";
	import { tickers } from "$lib/stores/dividends";
</script>

<aside class="flex flex-col justify-between border-r border-bg-accent bg-bg-sidebar p-2">
	<nav class="flex flex-col gap-2">
		<ul class="flex flex-col gap-1">
			<li>
				<MenuItem title="Portfolio" href="/portfolio">
					<PortfolioIcon />
				</MenuItem>
			</li>
			<li>
				<ul class="flex flex-col gap-1">
					{#each $accounts as account (account)}
						<li transition:scale animate:flip>
							<MenuItem title={account} href="/portfolio/{account}" subItem>
								<AccountIcon />
							</MenuItem>
						</li>
					{/each}
				</ul>
			</li>
			<li>
				<MenuItem title="Forecast" href="/forecast">
					<ForecastIcon />
				</MenuItem>
			</li>
			<li>
				<MenuItem title="Optimization" href="/optimization">
					<OptimizationIcon />
				</MenuItem>
			</li>
		</ul>
		{#if $tickers.tickers.length}
			<ul class="flex flex-col gap-1 border-t border-bg-medium pt-2" transition:scale>
				<li>
					<MenuItem title="Dividends">
						<DividendsIcon />
					</MenuItem>
				</li>
				<li>
					<ul class="flex flex-col gap-1">
						{#each $tickers.tickers as ticker (ticker)}
							<li transition:scale animate:flip>
								<MenuItem title={ticker} href="/dividends/{ticker}" subItem>
									<AccountIcon />
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
