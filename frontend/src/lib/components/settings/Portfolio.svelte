<script lang="ts">
	import H2 from "$lib/components/base/H2.svelte";
	import Switch from "$lib/components/base/Switch.svelte";
	import {
		portfolioSortByValue,
		togglePortfolioSortByValue,
		portfolioHideZeroPositions,
		togglePortfolioHideZeroPositions
	} from "$lib/stores/settings";
</script>

<section class="mt-4">
	<H2>Portfolio</H2>
	<ul class="pt-2">
		<li>
			<Switch label="sort value ascending" checked={$portfolioSortByValue} on:change={togglePortfolioSortByValue} />
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={$portfolioHideZeroPositions}
				on:change={togglePortfolioHideZeroPositions}
			/>
		</li>
	</ul>
</section>
