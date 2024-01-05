<script lang="ts">
	import LowerSidebar from "./LowerSidebar.svelte";
	import MenuItem from "./MenuItem.svelte";
	import PortfolioIcon from "$lib/icons/PortfolioIcon.svelte";
	import ForecastIcon from "$lib/icons/ForecastIcon.svelte";
	import OptimizationIcon from "$lib/icons/OptimizationIcon.svelte";
	import DividendsIcon from "$lib/icons/DividendsIcon.svelte";
	import AccountIcon from "$lib/icons/AccountIcon.svelte";

	export let accounts: string[];
</script>

<aside class="border-bg-accent bg-bg-sidebar flex flex-col justify-between border-r p-2">
	<nav class="flex flex-col gap-2">
		<ul class="flex flex-col gap-1">
			<MenuItem title="Portfolio" href="/portfolio">
				<PortfolioIcon />
			</MenuItem>
			{#each accounts as account (account)}
				<MenuItem title={account} href="/portfolio/{account.toLowerCase()}" subItem>
					<AccountIcon />
				</MenuItem>
			{/each}
			<MenuItem title="Forecast" href="/forecast">
				<ForecastIcon />
			</MenuItem>

			<MenuItem title="Optimization" href="/optimization">
				<OptimizationIcon />
			</MenuItem>
		</ul>
		<ul class="border-bg-medium border-t pt-2">
			<MenuItem title="Dividends" href="/dividends">
				<DividendsIcon />
			</MenuItem>
		</ul>
	</nav>
	<LowerSidebar />
</aside>
