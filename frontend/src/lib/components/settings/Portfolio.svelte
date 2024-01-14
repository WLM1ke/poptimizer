<script lang="ts">
	import H2 from "$lib/components/base/H2.svelte";
	import Switch from "$lib/components/base/Switch.svelte";
	import { settings } from "$lib/stores/settings";
</script>

<section class="mt-4">
	<H2>Portfolio</H2>
	<ul class="pt-2">
		<li>
			<Switch
				label="sort value ascending"
				checked={$settings.portfolio.sortByValue}
				on:change={() => {
					settings.update((settings) => {
						settings.portfolio.sortByValue = !settings.portfolio.sortByValue;

						return settings;
					});
				}}
			/>
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={$settings.portfolio.hideZeroPositions}
				on:change={() => {
					settings.update((settings) => {
						settings.portfolio.hideZeroPositions = !settings.portfolio.hideZeroPositions;

						return settings;
					});
				}}
			/>
		</li>
	</ul>
</section>
