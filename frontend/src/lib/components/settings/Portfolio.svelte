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
					settings.update((port) => {
						port.portfolio.sortByValue = !port.portfolio.sortByValue;

						return port;
					});
				}}
			/>
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={$settings.portfolio.hideZeroPositions}
				on:change={() => {
					settings.update((port) => {
						port.portfolio.hideZeroPositions = !port.portfolio.hideZeroPositions;

						return port;
					});
				}}
			/>
		</li>
	</ul>
</section>
