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
</script>

<aside class="border-bg-accent bg-bg-sidebar flex flex-col justify-between border-r p-2">
	<nav class="flex flex-col gap-2">
		<ul class="flex flex-col gap-1">
			<li>
				<MenuItem title="Portfolio" href="/portfolio">
					<PortfolioIcon />
				</MenuItem>
			</li>
			{#each $accounts as account (account)}
				<li transition:scale>
					<MenuItem title={account} href="/portfolio/{account}" subItem>
						<AccountIcon />
					</MenuItem>
				</li>
				<li />
			{/each}
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
		<ul class="border-bg-medium border-t pt-2">
			<li>
				<MenuItem title="Dividends" href="/dividends">
					<DividendsIcon />
				</MenuItem>
			</li>
		</ul>
	</nav>
	<LowerSidebar />
</aside>
