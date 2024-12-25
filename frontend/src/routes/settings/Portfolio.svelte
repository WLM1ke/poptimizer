<script lang="ts">
	import H2 from "$lib/components/H2.svelte";
	import Switch from "$lib/components/Switch.svelte";
	import { portfolioHideZeroPositions, portfolioSortByValue } from "$lib/state/settings.svelte";
	import {} from "$lib/stores/settings";
</script>

<section class="mt-4">
	<H2 text="Portfolio" />
	<ul class="pt-2">
		<li>
			<Switch
				label="sort value descending"
				checked={portfolioSortByValue.get()}
				onchange={portfolioSortByValue.toggle}
			/>
		</li>
		<li>
			<Switch
				label="hide zero positions"
				checked={portfolioHideZeroPositions.get()}
				onchange={portfolioHideZeroPositions.toggle}
			/>
		</li>
	</ul>
</section>
